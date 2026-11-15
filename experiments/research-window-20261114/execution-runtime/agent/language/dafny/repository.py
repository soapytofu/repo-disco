"""Opt-in, zero-model verification of an explicit, trusted repository snapshot.

This is staging, not a sandbox for adversarial Dafny includes or source code.
The existing single-program backend and model workers remain unchanged.
"""
from dataclasses import dataclass
from hashlib import sha256
import math
from pathlib import Path, PurePosixPath
import subprocess
import tempfile
import time

from language import VerificationOutcome, VerificationOutput


@dataclass
class RepositoryVerification:
    verification: VerificationOutput
    evidence: dict


def validate_snapshot(files, entry):
    if not files:
        raise ValueError('empty repository')
    for name, content in files.items():
        path = PurePosixPath(name)
        if (not isinstance(name, str) or path.is_absolute() or
                any(part in ('.', '..', '') for part in name.split('/')) or
                '\\' in name or '\x00' in name or name.startswith('-') or
                path.suffix != '.dfy' or not isinstance(content, bytes)):
            raise ValueError('expected canonical relative .dfy paths and byte contents')
    if entry not in files:
        raise ValueError('entry is not in repository snapshot')
    for name in files:
        if any(str(parent) in files for parent in PurePosixPath(name).parents):
            raise ValueError('file/directory path collision')


def verify_repository(files: dict[str, bytes], entry: str, timeout: float = 60):
    """Verify includes as well as the entry, once, and retain serializable evidence.

    Caller owns persistence of source bytes plus returned evidence. Files must be
    trusted/guarded: path validation does not constrain include directives inside
    their contents. GNU timeout bounds the verifier and its process group.
    """
    files = dict(files)
    validate_snapshot(files, entry)
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError('timeout must be finite and positive')
    command = ['timeout', '-k', '5s', f'{timeout}s', 'dafny', 'verify',
               '--verify-included-files', entry]
    hashes = {name: sha256(content).hexdigest() for name, content in sorted(files.items())}
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix='repodisco-') as directory:
        for name, content in files.items():
            dest = Path(directory) / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(content)
        try:
            proc = subprocess.run(command, cwd=directory, capture_output=True, text=True)
            code, stdout, stderr = proc.returncode, proc.stdout, proc.stderr
        except OSError as error:
            code, stdout, stderr = -1, '', str(error)
    # Explicit exit categories for the new API; leave legacy text heuristics alone.
    outcome = (VerificationOutcome.SUCCESS if code == 0 else
               VerificationOutcome.GOAL_UNPROVEN if code == 4 else VerificationOutcome.FAIL)
    category = {0: 'success', 4: 'proof_failure', 2: 'frontend_error',
                124: 'timeout', 137: 'killed', -1: 'launch_error'}.get(code, 'execution_error')
    evidence = dict(schema='repository-verification-v1', entry=entry,
                    source_sha256=hashes, command=command, exit_code=code,
                    outcome=outcome.name.lower(), category=category,
                    stdout=stdout, stderr=stderr,
                    elapsed_seconds=time.monotonic() - started,
                    model_calls=0, attempts=1)
    return RepositoryVerification(VerificationOutput(outcome, code, stdout, stderr), evidence)


async def snapshot_agenda_repository(agenda, paths: dict[str, str], entry: str):
    """Copy explicit relative-file -> agenda-object mappings without changing agenda.

    Caller must freeze/quiesce writers: the Agenda protocol has no atomic multi-
    object read. Returned hashes identify the exact snapshot, not current objects.
    """
    if len(set(paths.values())) != len(paths):
        raise ValueError('one agenda object cannot alias multiple repository files')
    files = {}
    for relative, object_path in paths.items():
        obj = await agenda.get_object(object_path)
        if obj is None or obj.content is None:
            raise ValueError(f'missing source object: {object_path}')
        files[relative] = bytes(obj.content)
    validate_snapshot(files, entry)
    return files
