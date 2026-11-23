"""Fake-process integration checks for the mandatory offline SDK regression."""
import contextlib
import copy
import io
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

import build_runtime as builder
import preflight


ROOT = Path(__file__).resolve().parent


def sdk():
    return dict(required=True, installed=True, boto3_version='SYNTHETIC-VERSION',
                botocore_version='SYNTHETIC-VERSION', client_created=False)


def probe_record():
    return dict(schema='repodisco-offline-sdk-auth-reproduction-v1', status='PASS',
                boto3_version='SYNTHETIC-VERSION', botocore_version='SYNTHETIC-VERSION',
                sources=dict(probe=builder.sha(ROOT / 'sdk_probe.py'),
                             transport=builder.sha(ROOT / 'bounded_requests.py'),
                             helper=builder.sha(ROOT / 'credential_transport.py'),
                             provider_error=builder.sha(ROOT / 'provider_error.py')),
                observations=[dict(case=case) for case in
                              ['legacy_pop_before_request', 'scoped_two_successes',
                               'scoped_error_terminal_no_retry', 'scoped_access_denied_metadata',
                               'scoped_throttled_metadata']],
                provider_requests=0, model_calls=0, native_calls=0,
                socket_connection_attempts=0, real_credentials_read=False,
                synthetic_responses_are_not_model_evidence=True)


class SdkRegressionIntegrationTests(unittest.TestCase):
    def test_sdk_absence_skips_only_optional_local_regression(self):
        with patch.object(preflight.subprocess, 'run', side_effect=AssertionError('process reached')):
            result = preflight.sdk_auth_regression(ROOT, dict(installed=False, required=False))
            self.assertEqual(result['status'], 'SKIPPED')
            self.assertEqual(result['scenarios'], 0)
            with self.assertRaisesRegex(ValueError, 'Required SDK authentication'):
                preflight.sdk_auth_regression(ROOT, dict(installed=False, required=True))

    def test_installed_sdk_probe_binds_sources_versions_and_full_transcript(self):
        raw = json.dumps(probe_record()).encode()
        with patch.object(preflight.subprocess, 'run',
                          return_value=subprocess.CompletedProcess([], 0, stdout=raw, stderr=b'fake stderr')) as run:
            result = preflight.sdk_auth_regression(ROOT, sdk())
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(result['scenarios'], 5)
        self.assertEqual(result['stdout'], raw.decode())
        self.assertEqual(result['stderr'], 'fake stderr')
        self.assertEqual(run.call_count, 1)
        command = run.call_args.args[0]
        self.assertEqual(command[1:], ['-B', str(ROOT / 'sdk_probe.py'), '--transport',
                                      str(ROOT / 'bounded_requests.py'), '--helper',
                                      str(ROOT / 'credential_transport.py')])
        self.assertEqual(run.call_args.kwargs['timeout'], 30)

    def test_nonpassing_malformed_drifted_or_nonisolated_probe_fails_closed(self):
        baseline = probe_record()
        malformed = (0, b'not JSON')
        failed_process = (1, json.dumps(baseline).encode())
        changed = []
        for key, value in [('status', 'FAIL'), ('model_calls', 1), ('provider_requests', 1),
                           ('socket_connection_attempts', 1), ('native_calls', 1),
                           ('real_credentials_read', True), ('boto3_version', 'DIFFERENT')]:
            item = copy.deepcopy(baseline); item[key] = value
            changed.append((0, json.dumps(item).encode()))
        item = copy.deepcopy(baseline); item['sources']['helper'] = '0' * 64
        changed.append((0, json.dumps(item).encode()))
        item = copy.deepcopy(baseline); item['observations'].pop()
        changed.append((0, json.dumps(item).encode()))
        for code, raw in [malformed, failed_process] + changed:
            with self.subTest(code=code, raw=raw), patch.object(preflight.subprocess, 'run',
                    return_value=subprocess.CompletedProcess([], code, stdout=raw, stderr=b'failure evidence')):
                result = preflight.sdk_auth_regression(ROOT, sdk())
            self.assertEqual(result['status'], 'FAIL')
            self.assertEqual(result['scenarios'], 0)
            self.assertEqual(result['stdout'], raw.decode())
            self.assertEqual(result['stderr'], 'failure evidence')
            self.assertIn('validation_error', result)

    def test_cli_requires_probe_after_import_and_before_unit_suite(self):
        for fail in (False, True):
            events = []
            def imports(required):
                self.assertTrue(required); events.append('import'); return sdk()
            def fake_run(command, **kwargs):
                if command[0] == 'bash':
                    events.append('shell'); return subprocess.CompletedProcess(command, 0)
                if str(ROOT / 'sdk_probe.py') in command:
                    events.append('sdk-auth')
                    return subprocess.CompletedProcess(command, int(fail),
                        stdout=json.dumps(probe_record()).encode(), stderr=b'')
                self.assertIn('unittest', command)
                events.append('unit-tests')
                return subprocess.CompletedProcess(command, 0, stdout=b'FAKE UNIT TEST RESULT\n')
            with self.subTest(fail=fail), patch.object(builder, 'collect', return_value={'repo_files': {}}), \
                    patch.object(preflight, 'sdk_preflight', imports), \
                    patch.object(preflight.subprocess, 'run', fake_run), \
                    contextlib.redirect_stdout(io.StringIO()) as stream:
                result = preflight.main(['--draft', '--require-sdk', '--repo', str(builder.REPO)])
            self.assertEqual(result, int(fail))
            self.assertEqual(events, ['shell', 'import', 'sdk-auth'] + ([] if fail else ['unit-tests']))
            record = json.loads(stream.getvalue())
            self.assertEqual(record['sdk_auth_regression']['status'], 'FAIL' if fail else 'PASS')
            self.assertEqual(record['model_calls'], 0)
            self.assertEqual(record['native_calls'], 0)


if __name__ == '__main__':
    unittest.main()
