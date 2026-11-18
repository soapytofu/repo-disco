"""Offline imports, fake-transport/native tests and shell syntax only.

No provider, SSH, Slurm, key inspection, verifier or connectivity probe is used.
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
    process = subprocess.run([sys.executable, '-B', '-m', 'unittest', '-v',
                              'test_ops', 'test_native_host', 'test_runner'], cwd=root,
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
                  sdk=sdk,
                  repo_files=len(pins), execution_code_sha256=code_pins,
                  all_input_pins_rechecked_after_tests=True,
                  all_input_pins_sha256=hashlib.sha256(json.dumps(pins, sort_keys=True, separators=(',', ':')).encode()).hexdigest())
    print(json.dumps(result, indent=2, sort_keys=True))
    return process.returncode


if __name__ == '__main__':
    sys.exit(main())
