"""Real imports and SDK configuration with fake transport/process; no remote requests."""
from importlib.metadata import version
from pathlib import Path
import json
import sys
import types
from unittest.mock import patch
from botocore.config import Config
import run_pilot as r
from bounded_requests import bedrock_transport

plan, tasks, trials = r.validate_bundle()
r.validate_runtime()
seen = {}


class FakeClient:
    def converse(self, **kwargs):
        seen['payload'] = kwargs
        return dict(output=dict(message=dict(content=[dict(text='FAKE')])),
                    ResponseMetadata=dict(RequestId='FAKE', RetryAttempts=0))


def factory(service, **kwargs):
    assert service == 'bedrock-runtime'
    seen['config'] = kwargs['config']
    return FakeClient()


request = r.load(r.ROOT / 'frozen-001' / trials[0]['request_path'])
bedrock_transport(plan, client_factory=factory, config_factory=Config)(request)
assert seen['payload'] == request
assert seen['config'].retries['total_max_attempts'] == 1
import logging_verifier as repository
seed=r.parent_parts(r.ROOT,trials[0])[2];commands=[]
def process(command,cwd,capture_output,text):
    commands.append(command)
    assert {p.name:p.read_bytes() for p in Path(cwd).glob('*.dfy')}==seed
    (Path(cwd)/'fake.csv').write_text('FAKE LOGGER BYTES')
    return types.SimpleNamespace(returncode=4,stdout='FAKE',stderr='')
with patch.object(repository.subprocess,'run',side_effect=process):evidence=repository.verify(seed)
assert commands==[['timeout','-k','5s','60s','dafny','verify','--verify-included-files','--log-format','csv','All.dfy']]
assert evidence['source_sha256']==r.hashes(seed) and evidence['csv']=={'fake.csv':'FAKE LOGGER BYTES'}
print(json.dumps(dict(status='PASS', model_calls=0, dafny_runs=0, planned_requests=r.LIMIT,
                     boto3=version('boto3'), botocore=version('botocore'),
                     sdk_total_max_attempts=1, exact_staged_source_bytes=True)))

import subprocess
p=subprocess.run([sys.executable,'-B','-m','unittest','discover','-s',str(r.ROOT),'-p','test_runner.py','-v'],capture_output=True,text=True,timeout=75)
print(p.stdout);print(p.stderr)
assert p.returncode==0,'Offline runner tests failed'
print(json.dumps(dict(status='PASS',offline_runner_tests=18,model_calls=0,dafny_runs=0)))
