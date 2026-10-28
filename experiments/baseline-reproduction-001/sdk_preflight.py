"""Actual installed SDK + Stubber, never a network/API request or real key."""
import json
from importlib.metadata import version
import boto3
from botocore.stub import Stubber
from bounded_requests import bedrock_transport,converse_request

def main():
    settings=dict(model_id='global.anthropic.claude-opus-4-5-20251101-v1:0',region='us-east-1',inference_config={'maxTokens':4096,'temperature':1.0})
    messages=[{'role':'system','content':'test'},{'role':'user','content':'test'}]
    holders=[]
    def factory(service,**kwargs):
        client=boto3.client(service,aws_access_key_id='offline-test',aws_secret_access_key='offline-test',**kwargs)
        assert client.meta.config.retries['total_max_attempts']==1
        stub=Stubber(client)
        stub.add_response('converse',dict(output={'message':{'role':'assistant','content':[{'text':'saved'}]}},
            stopReason='end_turn',usage={'inputTokens':2,'outputTokens':1,'totalTokens':3},metrics={'latencyMs':1},
            ResponseMetadata={'RequestId':'offline-request','RetryAttempts':0}),converse_request(messages,settings))
        stub.activate();holders.append(stub);return client
    response=bedrock_transport(settings,client_factory=factory)(messages)
    assert response['text']=='saved' and response['request_id']=='offline-request'
    for stub in holders:stub.assert_no_pending_responses();stub.deactivate()
    # Check the actual baseline parser dependency, not a local replacement.
    from code_output_parser import CodeOutputParser
    assert CodeOutputParser().parse('intro\n```diff\n+ assert true;\n```\n')=='+ assert true;\n'
    print(json.dumps(dict(sdk_stub_passed=True,parser_import_passed=True,actual_model_calls=0,
                         packages={p:version(p) for p in ['boto3','botocore','langchain-core']}),indent=2))

if __name__=='__main__':main()
