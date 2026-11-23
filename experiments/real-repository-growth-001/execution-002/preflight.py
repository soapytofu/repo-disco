"""Offline imports, intercepted SDK regression, fake tests and shell syntax.

No provider, SSH, Slurm, key inspection, verifier or connectivity probe is used.
The SDK regression uses dummy tokens, isolated empty configuration, a fake HTTP
boundary and forbidden socket connections. It is mandatory on the remote host.
``--draft`` checks a complete read-only proposed package before root freezes it.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

import build_runtime as builder


def sdk_preflight(required=False):
    """Import/version and Config construction only; never construct a client."""
    try:
        import boto3
        import botocore
        from botocore.config import Config
    except ImportError:
        builder.require(not required, 'Required boto3/botocore imports unavailable')
        return dict(required=required, installed=False, client_created=False, model_calls=0)
    config = Config(connect_timeout=15, read_timeout=180,
                    retries={'mode': 'standard', 'total_max_attempts': 1})
    expected = dict(connect_timeout=15, read_timeout=180, retries={'mode': 'standard', 'total_max_attempts': 1})
    observed = dict(connect_timeout=config.connect_timeout, read_timeout=config.read_timeout,
                    retries=config.retries)
    builder.require(observed == expected, 'No-retry SDK configuration differs')
    return dict(required=required, installed=True, boto3_version=boto3.__version__,
                botocore_version=botocore.__version__, config=observed,
                client_created=False, model_calls=0)


def sdk_auth_regression(root, sdk):
    """Run the exact installed SDK against a fake HTTP boundary in isolation."""
    if not sdk['installed']:
        builder.require(not sdk['required'], 'Required SDK authentication regression unavailable')
        return dict(status='SKIPPED', required=False, reason='SDK not installed locally',
                    scenarios=0, provider_requests=0, model_calls=0, native_calls=0)
    command = [sys.executable, '-B', str(root / 'sdk_probe.py'),
               '--transport', str(root / 'bounded_requests.py'),
               '--helper', str(root / 'credential_transport.py')]
    process = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
    result = dict(status='FAIL', required=sdk['required'], command=command,
                  returncode=process.returncode, stdout=process.stdout.decode(errors='replace'),
                  stderr=process.stderr.decode(errors='replace'), scenarios=0,
                  provider_requests=0, model_calls=0, native_calls=0)
    try:
        builder.require(process.returncode == 0, 'Offline SDK probe process failed')
        record = json.loads(process.stdout)
        builder.require(record['schema'] == 'repodisco-offline-sdk-auth-reproduction-v1'
                        and record['status'] == 'PASS', 'Offline SDK probe did not pass')
        for field in ('provider_requests', 'model_calls', 'native_calls', 'socket_connection_attempts'):
            builder.require(record[field] == 0, 'Offline SDK probe reported external activity')
        builder.require(record['real_credentials_read'] is False
                        and record['synthetic_responses_are_not_model_evidence'] is True,
                        'Offline SDK probe isolation missing')
        for field in ('boto3_version', 'botocore_version'):
            builder.require(record[field] == sdk[field], 'SDK versions changed during preflight')
        expected = dict(probe=builder.sha(root / 'sdk_probe.py'),
                        transport=builder.sha(root / 'bounded_requests.py'),
                        helper=builder.sha(root / 'credential_transport.py'))
        builder.require(record['sources'] == expected, 'SDK probe source mismatch')
        builder.require([o['case'] for o in record['observations']] ==
                        ['legacy_pop_before_request', 'scoped_two_successes',
                         'scoped_error_terminal_no_retry'], 'SDK regression scenarios differ')
        result.update(status='PASS', scenarios=3, record=record)
    except (ValueError, KeyError, TypeError) as exc:
        result['validation_error'] = str(exc)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=builder.REPO)
    parser.add_argument('--draft', action='store_true')
    parser.add_argument('--require-sdk', action='store_true')
    args = parser.parse_args(argv)
    repo = args.repo.resolve()
    root = repo / builder.REL
    if args.draft:
        pins = builder.collect(repo)['repo_files']
        runtime_sha = None
    else:
        import runtime
        runtime_sha = runtime.validate_package(repo)['runtime_sha256']
        pins = builder.read(root / 'runtime-freeze.json')['repo_files']
    subprocess.run(['bash', '-n', str(root / 'run.sbatch')], check=True, timeout=5)
    sdk = sdk_preflight(args.require_sdk)
    start = time.monotonic()
    sdk_auth = sdk_auth_regression(root, sdk)
    if sdk_auth['status'] == 'FAIL':
        process = subprocess.CompletedProcess([], 1, stdout=b'SDK regression failed; unit tests not started.\n')
    else:
        process = subprocess.run([sys.executable, '-B', '-m', 'unittest', '-v',
                                  'test_ops', 'test_native_host', 'test_runner',
                                  'test_credential_transport', 'test_sdk_preflight'], cwd=root,
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=220)
    code_pins = {name: digest for name, digest in pins.items() if name.startswith(builder.REL + '/')}
    # Drift while the fake tests ran is an integrity failure, even if tests passed.
    for name, digest in pins.items():
        builder.require(builder.sha(repo / name) == digest, 'Execution code changed during preflight')
    result = dict(schema='repodisco-growth-execution-offline-preflight-v1',
                  returncode=process.returncode, log=process.stdout.decode(errors='replace'),
                  python=sys.version, elapsed_seconds=time.monotonic() - start,
                  model_calls=0, native_calls=0, key_metadata_checks=0,
                  runtime_sha256=runtime_sha, draft=args.draft,
                  sdk=sdk, sdk_auth_regression=sdk_auth,
                  repo_files=len(pins), execution_code_sha256=code_pins,
                  all_input_pins_rechecked_after_tests=True,
                  all_input_pins_sha256=hashlib.sha256(json.dumps(pins, sort_keys=True, separators=(',', ':')).encode()).hexdigest())
    print(json.dumps(result, indent=2, sort_keys=True))
    return process.returncode


if __name__ == '__main__':
    sys.exit(main())
