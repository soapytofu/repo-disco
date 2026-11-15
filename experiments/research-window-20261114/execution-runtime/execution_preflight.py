"""Read-only staged validation and optional fake-only integration tests.

No key access, real client, provider requests, subprocess, Dafny, SSH or Slurm.
--require-installed-sdk checks package metadata, never network connectivity.
"""
import argparse
import importlib.util
from importlib.metadata import PackageNotFoundError, version
import io
import json
from pathlib import Path
import sys
import unittest

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);obj=importlib.util.module_from_spec(spec)
    sys.modules[name]=obj;spec.loader.exec_module(obj);return obj


def preflight(work_root,scope_sha256,execution_freeze_sha256,*,full_tests=False,require_installed_sdk=False):
    d=module('preflight_session_driver',ROOT/'session_driver.py')
    scope,freeze=d.validate_execution(work_root,scope_sha256,execution_freeze_sha256)
    env=dict(job_id='OFFLINE',partition='OFFLINE',host='OFFLINE',python=sys.version,
             versions=d.ENVIRONMENT,requeue=False,model_connectivity_calls=0)
    integration=d.RepairIntegration(work_root,scope,freeze,env,verifier=lambda files:None,clock=lambda:scope['deadline_epoch']-1)
    first=integration.supply(1,d.coordination.ZERO)
    d.require(first is not None,'Missing first frozen admission')
    packages={}
    for name in ('boto3','botocore'):
        try:packages[name]=version(name)
        except PackageNotFoundError:packages[name]=None
    if require_installed_sdk:d.require(packages=={n:d.ENVIRONMENT[n] for n in packages},'Installed SDK version mismatch')
    report=dict(static_freezes_and_first_admission='PASS',first_batch=first['batch_id'],frozen_calls=first['max_calls'],
                scope_sha256=scope_sha256,execution_freeze_sha256=execution_freeze_sha256,
                installed_sdk_versions=packages,installed_sdk_required=require_installed_sdk,
                real_model_requests=0,real_verifier_invocations=0,credentials_accessed=False,
                created_budget_or_session=False,full_fake_tests_requested=full_tests)
    if full_tests:
        tests=module('offline_execution_tests',ROOT/'test_execution.py')
        # All dependency sources come from the isolated, pinned input mirror.
        bundle=Path(work_root)/'batches'/first['batch_id']
        tests.FIXTURE=bundle/'frozen-001'
        tests.REPO=bundle/'inputs'
        suite=unittest.defaultTestLoader.loadTestsFromTestCase(tests.ExecutionTests)
        result=unittest.TextTestRunner(verbosity=2).run(suite)
        report.update(fake_test_methods=result.testsRun,fake_tests_passed=result.wasSuccessful())
        if not result.wasSuccessful():raise RuntimeError('Fake execution integration tests failed')
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work-root',type=Path,required=True)
    p.add_argument('--scope-sha256',required=True)
    p.add_argument('--execution-freeze-sha256',required=True)
    p.add_argument('--full-tests',action='store_true')
    p.add_argument('--require-installed-sdk',action='store_true')
    args=p.parse_args()
    report=preflight(args.work_root,args.scope_sha256,args.execution_freeze_sha256,
                    full_tests=args.full_tests,require_installed_sdk=args.require_installed_sdk)
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
