"""Focused fake-only timeout, evidence persistence and version-boundary checks."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import build_runtime as builder
import ops
import preflight
import runtime
import test_ops


ROOT = Path(__file__).resolve().parent


class PreflightTimeoutTests(unittest.TestCase):
    def test_unit_timeout_retains_partial_stdout_stderr_and_fixed_600s_limit(self):
        def fail(command, **kwargs):
            self.assertEqual(kwargs['timeout'], 600)
            self.assertIn('-u', command)
            raise subprocess.TimeoutExpired(command, 600, output=b'partial unit stdout\n', stderr=b'partial unit stderr\n')
        with patch.object(preflight.subprocess, 'run', fail):
            result = preflight.run_unit_suite(ROOT)
        self.assertEqual(result['returncode'], 124)
        self.assertTrue(result['timed_out'])
        self.assertEqual(result['log'], 'partial unit stdout\n')
        self.assertEqual(result['stderr'], 'partial unit stderr\n')
        self.assertEqual(result['timeout_partial_stdout'], result['log'])

    def test_sdk_records_and_incremental_unit_log_survive_timeout(self):
        with tempfile.TemporaryDirectory() as temp:
            evidence = Path(temp).resolve() / 'evidence'
            sdk = dict(installed=True, required=True, synthetic=True)
            auth = dict(status='PASS', scenarios=3, synthetic=True)
            def fail(command, **kwargs):
                if command[0] == 'bash':
                    return subprocess.CompletedProcess(command, 0)
                self.assertEqual(json.loads((evidence/'sdk-imports.json').read_text()), sdk)
                self.assertEqual(json.loads((evidence/'sdk-auth-regression.json').read_text()), auth)
                stream = kwargs['stdout']
                stream.write(b'progress survives before process returns\n')
                self.assertEqual((evidence/'unit-tests.log').read_bytes(), b'progress survives before process returns\n')
                raise subprocess.TimeoutExpired(command, 600, stderr=b'timeout stderr\n')
            with patch.object(builder, 'collect', return_value={'repo_files': {}}), \
                    patch.object(preflight, 'sdk_preflight', return_value=sdk), \
                    patch.object(preflight, 'sdk_auth_regression', return_value=auth), \
                    patch.object(preflight.subprocess, 'run', fail), contextlib.redirect_stdout(io.StringIO()) as output:
                code = preflight.main(['--draft', '--require-sdk', '--evidence-dir', str(evidence)])
            self.assertEqual(code, 124)
            result = json.loads(output.getvalue())
            self.assertEqual(result['schema'], 'repodisco-growth-execution-offline-preflight-v1')
            self.assertEqual(result['sdk_auth_regression'], auth)
            self.assertEqual(result['log'], 'progress survives before process returns\n')
            self.assertTrue(result['unit_suite']['timed_out'])
            self.assertEqual(json.loads((evidence/'result.json').read_text()), result)
            with self.assertRaises(FileExistsError):
                preflight.prepare_evidence(evidence, builder.REPO)
            with self.assertRaisesRegex(ValueError, 'outside the packaged repository'):
                preflight.prepare_evidence(ROOT/'forbidden-evidence', builder.REPO)

    def test_sdk_timeout_retains_output_without_altering_30s_bound(self):
        def fail(command, **kwargs):
            self.assertEqual(kwargs['timeout'], 30)
            raise subprocess.TimeoutExpired(command, 30, output=b'partial SDK stdout', stderr=b'partial SDK stderr')
        with patch.object(preflight.subprocess, 'run', fail):
            result = preflight.sdk_auth_regression(ROOT, dict(installed=True, required=True))
        self.assertEqual(result['status'], 'FAIL')
        self.assertEqual(result['returncode'], 124)
        self.assertTrue(result['timed_out'])
        self.assertEqual(result['stdout'], 'partial SDK stdout')
        self.assertEqual(result['stderr'], 'partial SDK stderr')

    def test_actual_ops_driver_retains_timeout_records_and_persistent_evidence(self):
        fixture = test_ops.ActualRemoteProgramTests()
        self.addCleanup(fixture.doCleanups)
        local, remote = fixture.setup_roots()
        observed = []
        def interrupted(command, **kwargs):
            self.assertEqual(kwargs['timeout'], 900)
            self.assertIn('--require-sdk', command)
            path = Path(command[command.index('--evidence-dir') + 1])
            self.assertEqual(path, remote/'preflight-evidence-001')
            self.assertFalse(path.is_relative_to(remote/'repo'))
            path.mkdir()
            (path/'sdk-auth-regression.json').write_text('{"status":"PASS","synthetic":true}')
            (path/'unit-tests.log').write_text('incremental output before outer interruption\n')
            raise subprocess.TimeoutExpired(command, 900, output=b'partial driver stdout', stderr=b'partial driver stderr')
        def transport(program, data=None, seconds=45, socket=None):
            observed.append(seconds)
            return fixture.execute_remote(program, remote, run=interrupted)
        with patch.object(ops, 'ROOT', local), patch.object(ops, 'remote', transport), \
                contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(ValueError, 'preflight failed'):
                ops.preflight()
        self.assertEqual(observed, [920])
        result = json.loads((local/'remote-preflight-001.json').read_text())
        self.assertEqual(result['returncode'], 124)
        self.assertTrue(result['driver_timed_out'])
        self.assertEqual(result['log'], 'partial driver stdout')
        self.assertEqual(result['driver_stderr'], 'partial driver stderr')
        self.assertEqual(result['preflight_evidence']['unit-tests.log']['text'],
                         'incremental output before outer interruption\n')
        self.assertFalse((local/'authorization.json').exists())
        self.assertFalse((remote/'model-001').exists())

    def test_separate_namespace_preserves_model_native_and_credential_components(self):
        self.assertTrue(builder.REL.endswith('/execution-003'))
        self.assertEqual(runtime.REL, builder.REL)
        self.assertEqual(ops.REL, builder.REL)
        self.assertTrue(ops.REMOTE_SUFFIX.endswith('/execution-003'))
        self.assertEqual(runtime.EXECUTION_ID, 'real-repository-growth-001-execution-003')
        self.assertEqual(ops.JOB_NAME, 'growth-model-8-003')
        self.assertEqual((runtime.LIMIT, ops.JOB_SECONDS), (8, 14400))
        origins = json.loads((ROOT/'copy-provenance.json').read_text())
        for name in ('run_pilot.py', 'bounded_requests.py', 'credential_transport.py',
                     'native_host.py', 'sdk_probe.py', 'review.py'):
            self.assertFalse(origins[name]['modified'])
            self.assertEqual(builder.sha(ROOT/name), origins[name]['sha256'])
            self.assertEqual((ROOT/name).read_bytes(), (builder.REPO/origins[name]['source']).read_bytes())
        self.assertIn('execution-003/run_pilot.py', (ROOT/'run.sbatch').read_text())


if __name__ == '__main__':
    unittest.main()
