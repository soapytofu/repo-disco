"""Sequential repository repair with immutable revisions and atomic promotion.

The caller supplies a bounded request transport and task-specific output guard.
No provider defaults, credentials, or automatic paid execution are defined here.
"""
from contextlib import contextmanager
from dataclasses import dataclass
import fcntl
import hashlib
import json
import os
from pathlib import Path
import tempfile
import uuid

from language.dafny.candidate import prepare_candidate, hashes, verify_candidate
from language.dafny.repository import validate_snapshot, verify_repository


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()


def atomic_json(path, value):
    fd,temp=tempfile.mkstemp(prefix='.'+path.name+'-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as stream:
            stream.write(canonical(value)+b'\n');stream.flush();os.fsync(stream.fileno())
        os.replace(temp,path)
        fd=os.open(path.parent,os.O_RDONLY)
        try:os.fsync(fd)
        finally:os.close(fd)
    finally:
        if os.path.exists(temp):os.unlink(temp)


@dataclass(frozen=True)
class Snapshot:
    revision: str
    files: dict
    manifest: dict


class RevisionStore:
    """Local POSIX store; one locked pointer update exposes a whole revision.

    Cooperating writers must use this API. No claim of transactional writes to
    Formal Disco's per-file agenda objects or non-POSIX/distributed filesystems.
    """
    def __init__(self,path):
        self.path=Path(path)

    @contextmanager
    def lock(self):
        with (self.path/'write.lock').open('a') as stream:
            fcntl.flock(stream,fcntl.LOCK_EX)
            try:yield
            finally:fcntl.flock(stream,fcntl.LOCK_UN)

    @classmethod
    def create(cls,path,files,manifest):
        validate_snapshot(files,manifest['entry'])
        cls.validate_manifest(files,manifest)
        store=cls(path);store.path.mkdir(parents=True,exist_ok=False)
        (store.path/'revisions').mkdir();(store.path/'attempts').mkdir()
        with store.lock():
            revision=store._write_revision(files,manifest,None,None)
            atomic_json(store.path/'HEAD.json',{'revision':revision})
        return store

    @staticmethod
    def validate_manifest(files,manifest):
        if set(manifest['dependencies'])!=set(files):raise ValueError('map must enumerate all files')
        if not set(manifest['editable'])<=set(files):raise ValueError('unknown editable file')
        for path,deps in manifest['dependencies'].items():
            if len(set(deps))!=len(deps) or not set(deps)<=set(files):raise ValueError('invalid dependency map')
        # Declared map is context metadata; actual source inclusion is checked by Dafny.

    def _write_revision(self,files,manifest,parent,evidence):
        revision=uuid.uuid4().hex;folder=self.path/'revisions'/revision;folder.mkdir()
        for name,content in files.items():
            target=folder/'files'/name;target.parent.mkdir(parents=True,exist_ok=True)
            with target.open('wb') as stream:
                stream.write(content);stream.flush();os.fsync(stream.fileno())
        meta=dict(revision=revision,parent=parent,manifest=manifest,source_sha256=hashes(files),verification=evidence)
        atomic_json(folder/'revision.json',meta)
        # Sync directories before exposing HEAD; failures leave only an orphan revision.
        for directory in sorted([p for p in folder.rglob('*') if p.is_dir()],key=lambda p:len(p.parts),reverse=True)+[folder,folder.parent]:
            fd=os.open(directory,os.O_RDONLY)
            try:os.fsync(fd)
            finally:os.close(fd)
        return revision

    def snapshot(self):
        revision=json.loads((self.path/'HEAD.json').read_text())['revision']
        if len(revision)!=32 or any(c not in '0123456789abcdef' for c in revision):raise ValueError('invalid revision ID')
        folder=self.path/'revisions'/revision;meta=json.loads((folder/'revision.json').read_text())
        files={name:(folder/'files'/name).read_bytes() for name in meta['source_sha256']}
        validate_snapshot(files,meta['manifest']['entry']);self.validate_manifest(files,meta['manifest'])
        if hashes(files)!=meta['source_sha256']:raise ValueError('revision source hash mismatch')
        return Snapshot(revision,files,meta['manifest'])

    def promote(self,base,candidate,result):
        evidence=result.evidence
        if result.verification.status!=0 or evidence['exit_code']!=0:raise ValueError('only verified candidates can be promoted')
        if evidence['source_sha256']!=hashes(candidate.files):raise ValueError('verification does not match candidate')
        if dict(candidate.base_hashes)!=hashes(base.files):raise ValueError('candidate base mismatch')
        if candidate.entry!=base.manifest['entry']:raise ValueError('entry mismatch')
        with self.lock():
            current=self.snapshot()
            if current.revision!=base.revision:raise ValueError('stale base revision')
            revision=self._write_revision(dict(candidate.files),base.manifest,base.revision,evidence)
            atomic_json(self.path/'HEAD.json',{'revision':revision})
            return revision


def context_for(snapshot,feedback):
    return dict(task='repair_repository',base_revision=snapshot.revision,
                manifest=snapshot.manifest,files={k:v.decode('utf-8') for k,v in sorted(snapshot.files.items())},
                feedback=feedback,instruction='Return only permitted file edits. Preserve contracts and all other files.')


def repair(store,gate,decode,guards,*,attempt_limit,verifier=verify_candidate,base_verifier=verify_repository):
    """Feedback-driven candidate loop. gate.invoke must enforce the request budget.

    decode(raw, snapshot) returns replacement byte strings using the frozen task
    parser. Rejected/failed edits never replace the base. Verification timeouts
    and execution errors stop the run. Each call preserves exact context/response.
    """
    if type(attempt_limit) is not int or attempt_limit<1:raise ValueError('invalid attempt limit')
    base=store.snapshot();records=[]
    if set(guards)!=set(base.manifest['editable']):raise ValueError('guard/editable mismatch')
    initial=base_verifier(base.files,base.manifest['entry'])
    atomic_json(store.path/('initial-verification-'+base.revision+'.json'),initial.evidence)
    if initial.verification.status==0:return [dict(outcome='ALREADY_VERIFIED',revision=base.revision)]
    if initial.verification.status!=4:return [dict(outcome='VERIFIER_STOP',exit_code=initial.verification.status)]
    feedback=dict(kind='initial',stdout=initial.verification.stdout,stderr=initial.verification.stderr)
    for index in range(attempt_limit):
        folder=store.path/'attempts'/uuid.uuid4().hex;folder.mkdir()
        prompt=context_for(base,feedback);atomic_json(folder/'context.json',prompt)
        try:raw=gate.invoke(prompt,task_id=base.manifest['task_id'],attempt_id=folder.name)
        except Exception as error:
            record=dict(outcome='REQUEST_STOP',error_type=type(error).__name__)
            atomic_json(folder/'result.json',record);records.append(record);break
        atomic_json(folder/'response.json',raw)
        try:
            replacements=decode(raw,base)
            candidate=prepare_candidate(base.files,replacements,entry=base.manifest['entry'],expected_hashes=hashes(base.files),guards=guards)
        except ValueError as error:
            record=dict(outcome='EDIT_REJECTED',reason=str(error))
            atomic_json(folder/'result.json',record);records.append(record);feedback=record;continue
        for name,content in candidate.files.items():
            target=folder/'candidate'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(content)
        result=verifier(candidate);atomic_json(folder/'verification.json',result.evidence)
        if result.verification.status==0:
            try:revision=store.promote(base,candidate,result)
            except ValueError as error:
                record=dict(outcome='PROMOTION_REJECTED',reason=str(error))
            else:record=dict(outcome='SUCCESS',revision=revision)
            atomic_json(folder/'result.json',record);records.append(record);break
        record=dict(outcome='PROOF_FAILURE' if result.verification.status==4 else 'VERIFIER_STOP',exit_code=result.verification.status)
        atomic_json(folder/'result.json',record);records.append(record)
        feedback=dict(**record,stdout=result.verification.stdout,stderr=result.verification.stderr)
        if result.verification.status!=4:break
    return records
