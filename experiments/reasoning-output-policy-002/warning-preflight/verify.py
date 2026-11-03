"""One compute-only verification with v2 guard replay; no provider or credentials."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def load(path): return json.loads(path.read_text())
def save(path, data):
    with path.open('x') as handle: handle.write(json.dumps(data, indent=2) + '\n')


def guarded_sources():
    sys.path.insert(0, str(ROOT / 'code'))
    from body_guard import parse_response
    task = load(ROOT / 'task.json')
    seed = {p.name: p.read_text() for p in (ROOT / 'seed').glob('*.dfy')}
    actual, decision = parse_response((ROOT / 'analyst-body.json').read_text(), seed, task)
    expected = {p.name: p.read_text() for p in (ROOT / 'candidate').glob('*.dfy')}
    if actual != expected or decision != load(ROOT / 'guard-decision.json'):
        raise ValueError('Guard/source evidence mismatch')
    return {name: text.encode() for name, text in actual.items()}


def main():
    if sys.argv[1:] != ['verification-001']: raise SystemExit('One fresh output only')
    host = socket.gethostname()
    if not os.environ.get('SLURM_JOB_ID') or 'login' in host: raise SystemExit('Compute allocation required')
    manifest = load(ROOT / 'manifest.json')
    for name, expected in manifest.items():
        if sha(ROOT / name) != expected: raise ValueError('Pinned runtime drift: ' + name)
    out = ROOT / 'verification-001'
    out.mkdir(exist_ok=False)
    for name in [*manifest, 'manifest.json']:
        dest = out / 'snapshot' / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, dest)
    sources = guarded_sources()
    from language.dafny.repository import verify_repository
    env = dict(job_id=os.environ['SLURM_JOB_ID'], host=host,
               partition=os.environ.get('SLURM_JOB_PARTITION'), python=sys.version,
               dafny=subprocess.run(['dafny', '--version'], capture_output=True, text=True, check=True, timeout=15).stdout.strip(),
               z3=subprocess.run(['z3', '--version'], capture_output=True, text=True, check=True, timeout=15).stdout.strip(),
               model_calls=0)
    save(out / 'environment.json', env)
    if env['dafny'] != '4.11.0+fcb2042d6d043a2634f0854338c08feeaaaf4ae2' or env['z3'] != 'Z3 version 4.12.1 - 64 bit':
        raise ValueError('Verifier version drift')
    evidence = verify_repository(sources, 'All.dfy', timeout=60).evidence
    if evidence['source_sha256'] != {name: hashlib.sha256(data).hexdigest() for name, data in sources.items()}:
        raise ValueError('Verifier/source mismatch')
    save(out / 'alias-case.json', dict(evidence=evidence, mutation=load(ROOT / 'mutation.json'), model_calls=0))
    save(out / 'summary.json', dict(completed_cases=1, exit_code=evidence['exit_code'],
                                  model_calls=0, original_pilot_score='18/24 unchanged'))
    print(json.dumps(dict(exit_code=evidence['exit_code'], category=evidence['category'], model_calls=0)), flush=True)
    if evidence['exit_code'] not in (0, 2, 4): raise SystemExit('Infrastructure stop; no retry')


if __name__ == '__main__': main()
