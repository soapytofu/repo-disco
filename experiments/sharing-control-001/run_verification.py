"""Verifier-only shared-proof controls. Run on a compute node, never login."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if not os.environ.get('SLURM_JOB_ID') or 'login' in socket.gethostname():
        raise SystemExit('Requires a Slurm compute node')
    source = Path(__file__).resolve().parent
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    for name in ['fixtures']:
        shutil.copytree(source / name, out / name)
    for name in ['checks.json', 'task.json', 'run_verification.py']:
        shutil.copy2(source / name, out / name)
    versions = {name: subprocess.run(command, text=True, capture_output=True, timeout=30).stdout.strip()
                for name, command in [('dafny', ['dafny', '--version']), ('z3', ['z3', '--version'])]}
    (out / 'environment.json').write_text(json.dumps(dict(versions=versions, host=socket.gethostname(), job_id=os.environ['SLURM_JOB_ID'], model_calls=0), indent=2)+'\n')
    results = []
    for check in json.loads((out / 'checks.json').read_text()):
        folder = out / 'fixtures' / check['variant']
        log = out / 'logs' / check['variant'] / Path(check['entry']).stem
        log.mkdir(parents=True)
        command = ['dafny', 'verify', '--verify-included-files', check['entry']]
        start = time.monotonic()
        try:
            proc = subprocess.run(command, cwd=folder, text=True, capture_output=True, timeout=60)
            code, stdout, stderr = proc.returncode, proc.stdout, proc.stderr
        except subprocess.TimeoutExpired as error:
            code = 124
            stdout, stderr = error.stdout or b'', error.stderr or b''
            stdout = stdout.decode(errors='replace') if isinstance(stdout, bytes) else stdout
            stderr = stderr.decode(errors='replace') if isinstance(stderr, bytes) else stderr
        (log / 'stdout.txt').write_text(stdout)
        (log / 'stderr.txt').write_text(stderr)
        match = re.search(r'(\d+) verified, (\d+) errors?', stdout)
        expected = code == check['expected_exit'] and match is not None and (int(match[2]) == 0 if code == 0 else int(match[2]) > 0)
        row = dict(check, exit_code=code, matches_expectation=expected, command=command, seconds=round(time.monotonic()-start,3), source_hashes={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(folder.glob('*.dfy'))})
        (log / 'result.json').write_text(json.dumps(row, indent=2)+'\n')
        results.append(row)
        (out / 'results.json').write_text(json.dumps(results, indent=2)+'\n')
        print(check['variant'],check['entry'],code,expected,flush=True)
    good = all(r['matches_expectation'] for r in results)
    (out / 'summary.json').write_text(json.dumps(dict(checks=len(results), all_expected=good, model_calls=0, finished_at_utc=datetime.now(timezone.utc).isoformat()),indent=2)+'\n')
    raise SystemExit(0 if good else 1)


if __name__ == '__main__':
    main()
