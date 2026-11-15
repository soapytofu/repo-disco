"""Thin compute adapter reusing the exact archived single-attempt verifier."""
from pathlib import Path, PurePosixPath
import hashlib
import importlib.util
import json
import re
import sys

ROOT=Path(__file__).resolve().parent
UPSTREAM='inputs/experiments/repair-diversity-expansion-001/witness/verify.py'
UPSTREAM_SHA256='4f29cefb7bba9b44287e4cb028cc55b9ebf1b11a6be37cae86c9405ae68935f9'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def load(path):return json.loads(Path(path).read_text())
def safe_file(root,name):
    relative=PurePosixPath(name)
    assert relative.parts and not relative.is_absolute() and '..' not in relative.parts and str(relative)==name,name
    path=Path(root)
    for part in relative.parts:
        path/=part;assert not path.is_symlink(),name
    assert path.is_file() and path.resolve().is_relative_to(Path(root).resolve()),name
    return path

assert sha(safe_file(ROOT,UPSTREAM).read_bytes())==UPSTREAM_SHA256
spec=importlib.util.spec_from_file_location('pipeline_maps_archived_verifier',ROOT/UPSTREAM)
upstream=importlib.util.module_from_spec(spec);spec.loader.exec_module(upstream)

def validate_pins(root=None):
    root=Path(ROOT if root is None else root)
    runtime=load(root/'runtime-manifest.json');fixtures=load(root/'fixture-manifest.json')
    assert {'verify.py','verify.sbatch','build.py','test_structure.py','fixture-manifest.json'}<=set(runtime)
    assert {'tasks.json','cases.json','file_rules.json','control-aliases.json'}<=set(fixtures)
    pins={}
    for manifest in (runtime,fixtures):
        for name,digest in manifest.items():
            assert re.fullmatch('[0-9a-f]{64}',digest)
            assert name not in pins or pins[name]==digest
            assert sha(safe_file(root,name).read_bytes())==digest,name
            pins[name]=digest
    assert sha(safe_file(root,UPSTREAM).read_bytes())==UPSTREAM_SHA256
    actual={}
    for folder in ('fixtures','templates'):
        for path in sorted((root/folder).rglob('*')):
            assert not path.is_symlink(),str(path)
            if path.is_dir():continue
            assert path.is_file() and path.suffix=='.dfy',str(path)
            actual[path.relative_to(root).as_posix()]=sha(path.read_bytes())
    for name in ('tasks.json','cases.json','file_rules.json','control-aliases.json'):
        actual[name]=sha((root/name).read_bytes())
    assert actual==fixtures,'Fixture inventory mismatch'
    tasks={task['task_id']:task for task in load(root/'tasks.json')}
    rules=load(root/'file_rules.json');cases=load(root/'cases.json')
    assert len(tasks)==2 and len(cases)==21 and len({case['case_id'] for case in cases})==21
    assert {status:sum(case['expected']==status for case in cases) for status in ('success','proof_failure','resolution_failure')}==dict(success=4,proof_failure=15,resolution_failure=2)
    for task in tasks.values():
        assert task['editable_files']==['HelperA.dfy','HelperB.dfy'] and task['sharing']=='pipeline'
        assert task['file_rules']==rules[task['task_id']]
        template=root/task['template_path']
        assert {p.name:sha(p.read_bytes()) for p in template.glob('*.dfy')}==task['source_sha256']
    for case in cases:
        assert case['task_id'] in tasks and case['entry']=='All.dfy'
        assert case['expected_diagnostic'] in ('none',*upstream.DIAGNOSTICS)
        assert {p.name:sha(p.read_bytes()) for p in (root/case['path']).glob('*.dfy')}==case['source_sha256']
    byid={case['case_id']:case for case in cases}
    aliases=load(root/'control-aliases.json');assert len(aliases)==4
    for alias in aliases:
        assert alias['logical_case_id'] not in byid and not alias['new_verifier_call'] and not alias['independent_observation']
        original=byid[alias['evidence_alias_of']]
        assert alias['source_sha256']==original['source_sha256'] and alias['source_path']==original['path']
        assert alias['expected']==original['expected']
    return pins

upstream.ROOT=ROOT
upstream.validate_pins=validate_pins
run=upstream.run
verify=upstream.verify
matches=upstream.matches
classify=upstream.classify
diagnostic_details=upstream.diagnostic_details
COMMAND=upstream.COMMAND

if __name__=='__main__':
    assert sys.argv[1:]==['verification-001']
    raise SystemExit(0 if run('verification-001') else 1)
