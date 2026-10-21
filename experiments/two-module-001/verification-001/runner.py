"""Verifier-only two-module experiment. No provider/API credentials are used."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import time


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--dafny', default='dafny')
    args = parser.parse_args()
    source = Path(__file__).resolve().parent
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    shutil.copytree(source / 'fixtures', out / 'fixtures')
    shutil.copy2(source / 'repository-manifest.json', out / 'repository-manifest.json')
    shutil.copy2(__file__, out / 'runner.py')
    tool = shutil.which(args.dafny)
    if not tool:
        raise SystemExit('Dafny executable not found')
    versions = {}
    for name, command in [('dafny', [tool, '--version']), ('z3', ['z3', '--version'])]:
        p = subprocess.run(command, capture_output=True, text=True, timeout=30)
        versions[name] = dict(command=command, exit_code=p.returncode, stdout=p.stdout, stderr=p.stderr)
    write_json(out / 'environment.json', {'started_at_utc':datetime.now(timezone.utc).isoformat(),'tools':versions,'model_calls':0,'verification_timeout_seconds':60})
    expected = {'baseline':[True,True,True], 'implementation-bug':[False,True,False],
                'weakened-contract-control':[True,False,False], 'reference-repair':[True,True,True]}
    checks = [('provider',['Arithmetic.dfy']), ('client_only',['Client.dfy']),
              ('whole_repository',['--verify-included-files','Client.dfy'])]
    records = []
    for variant, passes in expected.items():
        folder = out / 'fixtures' / variant
        for (scope, arguments), want_pass in zip(checks, passes):
            log = out / 'checks' / variant / scope
            log.mkdir(parents=True)
            command = [tool, 'verify'] + arguments
            start = time.monotonic()
            try:
                p = subprocess.run(command, cwd=folder, capture_output=True, text=True, timeout=60)
                code, stdout, stderr = p.returncode, p.stdout, p.stderr
            except subprocess.TimeoutExpired as error:
                code = 124
                stdout = error.stdout or b''
                stderr = error.stderr or b''
                stdout = stdout.decode(errors='replace') if isinstance(stdout,bytes) else stdout
                stderr = stderr.decode(errors='replace') if isinstance(stderr,bytes) else stderr
            (log / 'stdout.txt').write_text(stdout)
            (log / 'stderr.txt').write_text(stderr)
            match = re.search(r'(\d+) verified, (\d+) errors?', stdout)
            passed = code == 0 and match is not None and int(match[1]) > 0 and int(match[2]) == 0
            verification_failure = code == 4 and match is not None and int(match[2]) > 0
            observed = 'PASS' if passed else ('VERIFICATION_FAILURE' if verification_failure else 'INFRASTRUCTURE_OR_PARSE_ERROR')
            record = dict(variant=variant,scope=scope,command=command,source_directory=str(folder),
                          source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(folder.glob('*.dfy'))},
                          exit_code=code,outcome=observed,expected_pass=want_pass,
                          matches_expectation=passed if want_pass else verification_failure,
                          elapsed_seconds=round(time.monotonic()-start,3),
                          verified_obligations=int(match[1]) if match else None, verifier_errors=int(match[2]) if match else None)
            write_json(log / 'result.json',record)
            records.append(record)
            write_json(out / 'results.json', records)
            print(variant, scope, observed, 'expected=',record['matches_expectation'],flush=True)
    unchanged = all((out/'fixtures'/v/'Client.dfy').read_bytes()==(out/'fixtures/baseline/Client.dfy').read_bytes() for v in expected)
    restored = (out/'fixtures/reference-repair/Arithmetic.dfy').read_bytes()==(out/'fixtures/baseline/Arithmetic.dfy').read_bytes()
    write_json(out/'summary.json',dict(model_calls=0,checks=len(records),all_expected=all(r['matches_expectation'] for r in records),client_unchanged=unchanged,reference_repair_restores_baseline=restored,completed_at_utc=datetime.now(timezone.utc).isoformat()))
    if not all(r['matches_expectation'] for r in records) or not unchanged or not restored:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
