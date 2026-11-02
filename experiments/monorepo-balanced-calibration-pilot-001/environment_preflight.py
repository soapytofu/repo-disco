"""Real environment imports/configuration; fake client only, zero requests/Dafny."""
import json
import unittest
from importlib.metadata import version
from botocore.config import Config
import run_pilot as r
from bounded_requests import bedrock_transport
from test_runner import Runner

settings, tasks, trials = r.validate_bundle()
r.validate_runtime()
seen = {}


class FakeClient:
    def converse(self, **kwargs):
        seen['payload'] = kwargs
        return {'output': {'message': {'content': [{'text': 'FAKE'}]}},
                'ResponseMetadata': {'RequestId': 'OFFLINE', 'RetryAttempts': 0}}


def factory(service, **kwargs):
    assert service == 'bedrock-runtime'
    seen['config'] = kwargs['config']
    return FakeClient()


messages = [{'role': 'system', 'content': 'offline'}, {'role': 'user', 'content': 'offline'}]
response = bedrock_transport(settings, client_factory=factory, config_factory=Config)(messages)
assert response['request_id'] == 'OFFLINE'
assert seen['config'].retries['total_max_attempts'] == 1
assert seen['config'].connect_timeout == 15 and seen['config'].read_timeout == 180
assert seen['payload']['inferenceConfig'] == settings['inference_config']
print(json.dumps(dict(inputs_and_runtime_valid=True, planned_trials=len(trials), tasks=len(tasks),
                     boto3=version('boto3'), botocore=version('botocore'),
                     sdk_total_max_attempts=1, real_requests=0, dafny_runs=0)), flush=True)
suite = unittest.TestSuite(Runner(name) for name in [
    'test_sdk_no_retry_and_exact_converse_payload',
    'test_body_assembly_preserves_contracts_and_rejects_full_files',
    'test_import_uses_pinned_grammar_and_restores_cache'])
if not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful():
    raise SystemExit(1)
