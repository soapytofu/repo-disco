"""Exact-SDK authentication regression with dummy tokens and no network access.

The real SDK prepares/signs each request, but an in-memory HTTP boundary returns
synthetic responses. All socket connections are forbidden; credential/config
providers see only newly created empty files and an isolated environment.
This is not an API availability check or a model/native-verifier invocation.
"""
import argparse
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import traceback
from unittest.mock import patch


TOKEN = 'OFFLINE_DUMMY_TOKEN_NOT_A_CREDENTIAL'
ENV = 'AWS_BEARER_TOKEN_BEDROCK'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--transport', type=Path, required=True)
    parser.add_argument('--helper', type=Path, required=True)
    args = parser.parse_args()
    assert digest(args.transport) == '5e19a5855ae32f1f3ca6bcbb7db136aeab35c1d83f8e7f77fe582fec83dd366a'
    for name, path in [('bounded_requests', args.transport), ('credential_transport', args.helper)]:
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
    transport = sys.modules['bounded_requests']
    helper = sys.modules['credential_transport']
    network_attempts = []

    def forbidden_network(*args, **kwargs):
        network_attempts.append('blocked socket connection')
        raise RuntimeError('Offline regression forbids all network connections')

    settings = dict(region='us-east-1', model_id='offline.invalid-model',
                    inference_config=dict(maxTokens=16, temperature=1.0))
    payload = dict(modelId=settings['model_id'], system=[{'text': 'Offline synthetic test.'}],
                   messages=[{'role': 'user', 'content': [{'text': 'No network is allowed.'}]}],
                   inferenceConfig=settings['inference_config'])
    observations = []
    with tempfile.TemporaryDirectory(prefix='repodisco-offline-sdk-') as folder:
        empty = Path(folder) / 'empty-config'
        empty.write_text('')
        environment = dict(PATH=os.environ.get('PATH', ''), LANG='C.UTF-8',
                           PYTHONDONTWRITEBYTECODE='1', AWS_EC2_METADATA_DISABLED='true',
                           AWS_CONFIG_FILE=str(empty), AWS_SHARED_CREDENTIALS_FILE=str(empty),
                           BOTO_CONFIG=str(empty), AWS_DEFAULT_REGION='us-east-1')
        with patch.dict(os.environ, environment, clear=True), \
                patch.object(socket.socket, 'connect', forbidden_network), \
                patch.object(socket, 'create_connection', forbidden_network):
            import boto3
            import botocore
            from botocore.awsrequest import AWSResponse
            from botocore.exceptions import EndpointConnectionError, NoCredentialsError

            def make_factory(*, fail=False):
                calls = dict(factories=0, intercepted_http=0, bearer_headers=[], retry_configuration=[])

                def factory(*args, **kwargs):
                    calls['factories'] += 1
                    client = boto3.session.Session().client(*args, **kwargs)
                    calls['retry_configuration'].append(client.meta.config.retries)

                    def send(request):
                        calls['intercepted_http'] += 1
                        value = next((v for k, v in request.headers.items() if k.lower() == 'authorization'), None)
                        if isinstance(value, bytes):
                            value = value.decode()
                        calls['bearer_headers'].append(value == 'Bearer ' + TOKEN)
                        assert value == 'Bearer ' + TOKEN, 'Expected synthetic bearer authentication'
                        if fail:
                            raise EndpointConnectionError(endpoint_url='https://offline.invalid')
                        body = json.dumps(dict(output=dict(message=dict(role='assistant', content=[dict(text='{}')])),
                                               stopReason='end_turn', usage=dict(inputTokens=1, outputTokens=1, totalTokens=2),
                                               metrics=dict(latencyMs=0))).encode()

                        class Raw:
                            def stream(self, *args, **kwargs):
                                yield body

                        return AWSResponse(request.url, 200,
                            {'content-type': 'application/json',
                             'x-amzn-requestid': 'synthetic-no-network-' + str(calls['intercepted_http'])}, Raw())

                    client._endpoint.http_session.send = send
                    return client
                return factory, calls

            # Reproduce the frozen runner's exact token lifetime: client creation
            # sees the token, but the later request does not.
            factory, calls = make_factory()
            os.environ[ENV] = TOKEN
            old = transport.bedrock_transport(settings, client_factory=factory)
            os.environ.pop(ENV)
            try:
                old(payload)
            except NoCredentialsError:
                observations.append(dict(case='legacy_pop_before_request', error_type='NoCredentialsError',
                                         traceback=traceback.format_exc(), **calls))
            else:
                raise AssertionError('Legacy failure did not reproduce')
            assert calls['intercepted_http'] == 0 and ENV not in os.environ

            # The proposed wrapper must survive request-time SDK authentication
            # on two independent calls without reloading the private token.
            factory, calls = make_factory()
            loads = []

            def loader():
                loads.append('synthetic load')
                return TOKEN

            fixed = helper.ScopedBearerTransport(settings, loader,
                transport_factory=lambda s: transport.bedrock_transport(s, client_factory=factory))
            first = fixed(payload)
            assert ENV not in os.environ
            second = fixed(payload)
            assert ENV not in os.environ
            assert len(loads) == 1 and calls['factories'] == 1 and calls['intercepted_http'] == 2
            assert all(calls['bearer_headers'])
            assert first['request_id'] != second['request_id']
            assert first['retry_attempts'] == second['retry_attempts'] == 0
            observations.append(dict(case='scoped_two_successes', token_loads=len(loads),
                                     environment_restored_between_calls=True, **calls))

            # A synthetic HTTP-boundary failure must not trigger an SDK retry,
            # leave the token in the environment, or allow a second dispatch.
            factory, calls = make_factory(fail=True)
            fixed = helper.ScopedBearerTransport(settings, lambda: TOKEN,
                transport_factory=lambda s: transport.bedrock_transport(s, client_factory=factory))
            try:
                fixed(payload)
            except EndpointConnectionError:
                pass
            else:
                raise AssertionError('Synthetic failure was hidden')
            assert ENV not in os.environ and calls['intercepted_http'] == 1
            try:
                fixed(payload)
            except RuntimeError:
                pass
            else:
                raise AssertionError('Terminal transport allowed another attempt')
            assert calls['intercepted_http'] == 1 and ENV not in os.environ
            observations.append(dict(case='scoped_error_terminal_no_retry',
                                     environment_restored_after_error=True, **calls))
            assert not network_attempts
            sdk_root = Path(botocore.__file__).parent
            sdk_sources = {n: digest(sdk_root / n) for n in
                           ['client.py', 'auth.py', 'signers.py', 'utils.py', 'tokens.py']}
            result = dict(schema='repodisco-offline-sdk-auth-reproduction-v1', status='PASS',
                          python=sys.version, boto3_version=boto3.__version__, botocore_version=botocore.__version__,
                          sources=dict(probe=digest(__file__), transport=digest(args.transport), helper=digest(args.helper)),
                          sdk_source_sha256=sdk_sources, observations=observations,
                          socket_connection_attempts=len(network_attempts), provider_requests=0,
                          model_calls=0, native_calls=0, real_credentials_read=False,
                          synthetic_responses_are_not_model_evidence=True,
                          actual_stopped_run_ledger_is_not_changed=True)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
