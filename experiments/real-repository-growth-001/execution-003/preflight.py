"""Offline imports, intercepted SDK regression, fake tests and shell syntax.

No provider, SSH, Slurm, key inspection, verifier or connectivity probe is used.
The SDK regression uses dummy tokens, isolated empty configuration, a fake HTTP
boundary and forbidden socket connections. It is mandatory on the remote host.
``--draft`` checks a complete read-only proposed package before root freezes it.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import build_runtime as builder

UNIT_SUITE_SECONDS = 600


def decoded(value):
    return value.decode(errors='replace') if isinstance(value, bytes) else (value or '')


def save_evidence(directory, name, value):
    if directory is not None:
        with (directory / name).open('xb') as stream:
            stream.write((json.dumps(value, indent=2, sort_keys=True) + '\n').encode())
            stream.flush()
            os.fsync(stream.fileno())


def prepare_evidence(directory, repo):
    if directory is None:
        return None
    path = directory.absolute()
    builder.require(not any(p.is_symlink() for p in (path, *path.parents)), 'Symlinked preflight evidence path')
    path = path.resolve()
    builder.require(not path.is_relative_to(repo), 'Preflight evidence must be outside the packaged repository')
    path.mkdir(parents=True, exist_ok=False)
    save_evidence(path, 'started.json', dict(status='STARTED', model_calls=0, native_calls=0,
                                           unit_suite_seconds=UNIT_SUITE_SECONDS))
    return path


def run_unit_suite(root, evidence=None):
    command = [sys.executable, '-B', '-u', '-m', 'unittest', '-v',
               'test_ops', 'test_native_host', 'test_runner', 'test_credential_transport',
               'test_sdk_preflight', 'test_preflight_timeout']
    stream = (evidence / 'unit-tests.log').open('xb', buffering=0) if evidence is not None else None
    timed_out = False
    try:
        try:
            process = subprocess.run(command, cwd=root,
                                     stdout=stream if stream is not None else subprocess.PIPE,
                                     stderr=subprocess.STDOUT, timeout=UNIT_SUITE_SECONDS)
            code, partial_stdout, partial_stderr = process.returncode, process.stdout, process.stderr
        except subprocess.TimeoutExpired as exc:
            code, partial_stdout, partial_stderr = 124, exc.output, exc.stderr
            timed_out = True
    finally:
        if stream is not None:
            stream.close()
    log = (evidence / 'unit-tests.log').read_text(errors='replace') if evidence is not None else decoded(partial_stdout)
    result = dict(command=command, returncode=code, timed_out=timed_out,
                  timeout_seconds=UNIT_SUITE_SECONDS, log=log,
                  stderr=decoded(partial_stderr), timeout_partial_stdout=decoded(partial_stdout) if timed_out else '',
                  timeout_partial_stderr=decoded(partial_stderr) if timed_out else '')
    save_evidence(evidence, 'unit-result.json', result)
    return result


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
    timed_out = False
    try:
        process = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
    except subprocess.TimeoutExpired as exc:
        process = subprocess.CompletedProcess(command, 124, stdout=exc.output or b'', stderr=exc.stderr or b'')
        timed_out = True
    result = dict(status='FAIL', required=sdk['required'], command=command,
                  returncode=process.returncode, stdout=decoded(process.stdout),
                  stderr=decoded(process.stderr), scenarios=0, timed_out=timed_out, timeout_seconds=30,
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
    parser.add_argument('--evidence-dir', type=Path)
    args = parser.parse_args(argv)
    repo = args.repo.resolve()
    root = repo / builder.REL
    evidence = prepare_evidence(args.evidence_dir, repo)
    if args.draft:
        pins = builder.collect(repo)['repo_files']
        runtime_sha = None
    else:
        import runtime
        runtime_sha = runtime.validate_package(repo)['runtime_sha256']
        pins = builder.read(root / 'runtime-freeze.json')['repo_files']
    subprocess.run(['bash', '-n', str(root / 'run.sbatch')], check=True, timeout=5)
    sdk = sdk_preflight(args.require_sdk)
    save_evidence(evidence, 'sdk-imports.json', sdk)
    start = time.monotonic()
    sdk_auth = sdk_auth_regression(root, sdk)
    save_evidence(evidence, 'sdk-auth-regression.json', sdk_auth)
    if sdk_auth['status'] == 'FAIL':
        units = dict(returncode=1, log='SDK regression failed; unit tests not started.\n',
                     stderr='', timed_out=False, timeout_seconds=UNIT_SUITE_SECONDS, started=False)
    else:
        units = run_unit_suite(root, evidence)
    code_pins = {name: digest for name, digest in pins.items() if name.startswith(builder.REL + '/')}
    # Drift while the fake tests ran is an integrity failure, even if tests passed.
    for name, digest in pins.items():
        builder.require(builder.sha(repo / name) == digest, 'Execution code changed during preflight')
    result = dict(schema='repodisco-growth-execution-offline-preflight-v1',
                  returncode=units['returncode'], log=units['log'], unit_suite=units,
                  python=sys.version, elapsed_seconds=time.monotonic() - start,
                  model_calls=0, native_calls=0, key_metadata_checks=0,
                  runtime_sha256=runtime_sha, draft=args.draft,
                  sdk=sdk, sdk_auth_regression=sdk_auth,
                  evidence_directory=str(evidence) if evidence is not None else None,
                  repo_files=len(pins), execution_code_sha256=code_pins,
                  all_input_pins_rechecked_after_tests=True,
                  all_input_pins_sha256=hashlib.sha256(json.dumps(pins, sort_keys=True, separators=(',', ':')).encode()).hexdigest())
    save_evidence(evidence, 'result.json', result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return result['returncode']


if __name__ == '__main__':
    sys.exit(main())
