"""Real package/import preflight with fake SDK/verifier process; no live calls."""
import json,sys,types,unittest
from importlib.metadata import version
from pathlib import Path
from unittest.mock import patch
from botocore.config import Config
import run_pilot as r
from bounded_requests import bedrock_transport
from test_runner import Runner

settings,tasks,trials=r.validate_bundle();r.validate_runtime()
seen={}

class FakeClient:
 def converse(self,**kwargs):
  seen['payload']=kwargs
  return {'output':{'message':{'content':[{'text':'FAKE'}]}},'ResponseMetadata':{'RequestId':'OFFLINE','RetryAttempts':0}}

def factory(service,**kwargs):
 assert service=='bedrock-runtime';seen['config']=kwargs['config'];return FakeClient()

request=r.load(r.ROOT/'frozen-001'/trials[0]['request_path'])
response=bedrock_transport(settings,client_factory=factory,config_factory=Config)(request)
assert response['request_id']=='OFFLINE' and seen['payload']==request
assert seen['config'].retries['total_max_attempts']==1
assert seen['config'].connect_timeout==15 and seen['config'].read_timeout==180
sys.path.insert(0,str(r.ROOT/'frozen-001/verifier'))
import language.dafny.repository as repository
assert Path(repository.__file__).resolve().is_relative_to(r.ROOT/'frozen-001/verifier')
seeds=r.sources(r.ROOT,tasks[0]);calls=[]

def fake_process(command,cwd,capture_output,text):
 calls.append(command)
 assert {p.name:p.read_bytes() for p in Path(cwd).glob('*.dfy')}==seeds
 return types.SimpleNamespace(returncode=4,stdout='FAKE expected proof failure',stderr='')

with patch.object(repository.subprocess,'run',side_effect=fake_process):
 evidence=repository.verify_repository(seeds,'All.dfy',timeout=60).evidence
assert len(calls)==1 and calls[0]==['timeout','-k','5s','60s','dafny','verify','--verify-included-files','All.dfy']
assert evidence['source_sha256']==r.hashes(seeds) and evidence['exit_code']==4
print(json.dumps(dict(inputs_and_runtime_valid=True,planned_trials=len(trials),tasks=len(tasks),
 boto3=version('boto3'),botocore=version('botocore'),sdk_total_max_attempts=1,
 real_requests=0,dafny_runs=0,verifier_import_and_fake_staging=True)),flush=True)
suite=unittest.TestSuite(Runner(name) for name in [
 'test_sdk_no_retry_and_exact_converse_payload',
 'test_body_assembly_preserves_contracts_and_rejects_full_files',
 'test_guard_loads_only_exact_pinned_body_module'])
if not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful():raise SystemExit(1)
