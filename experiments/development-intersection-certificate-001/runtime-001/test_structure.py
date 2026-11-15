"""Offline-only import and fake-process preflight; no real verifier or network."""
from pathlib import Path
import base64
import contextlib
import importlib.util
import io
import json
import os
import shutil
import socket
import subprocess
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent


def module(name, root=ROOT):
    spec = importlib.util.spec_from_file_location(name, root / 'verify.py')
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


# All possible subprocess or network actions fail unless a test explicitly
# replaces the verifier's subprocess.run with its finite fake implementation.
with patch.object(subprocess, 'run', side_effect=AssertionError('No process during import')), \
     patch.object(subprocess, 'Popen', side_effect=AssertionError('No child process')), \
     patch.object(socket, 'socket', side_effect=AssertionError('No network')):
    v = module('intersection_runtime_offline_tests')


@contextlib.contextmanager
def isolated_copy():
    with tempfile.TemporaryDirectory(prefix='intersection-runtime-fake-') as folder:
        root = Path(folder) / 'bundle'
        shutil.copytree(ROOT, root, ignore=shutil.ignore_patterns('__pycache__', 'verification-001'))
        yield root


def fake_result(case):
    if case['expected'] == 'success':
        return b'Dafny program verifier finished with 17 verified, 0 errors\r\n', 0
    if case['expected'] == 'resolution_failure':
        return (b'HelperA.dfy(12,1): Error: member DirectWitness does not exist in module Api\n'
                b'1 resolution/type errors detected in All.dfy\n'), 2
    messages = {
        'precondition': 'a precondition for this call could not be proved',
        'postcondition': 'a postcondition could not be proved on this return path',
    }
    return ('HelperA.dfy(12,1): Error: ' + messages[case['expected_diagnostic']] +
            '\nDafny program verifier finished with 16 verified, 1 error\n').encode(), 4


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.no_process = patch.object(subprocess, 'Popen', side_effect=AssertionError('No child process'))
        self.no_network = patch.object(socket, 'socket', side_effect=AssertionError('No network'))
        self.no_run = patch.object(subprocess, 'run', side_effect=AssertionError('Only explicit fake processes allowed'))
        for item in (self.no_process, self.no_network, self.no_run):
            item.start()
            self.addCleanup(item.stop)

    def test_isolated_import_and_exact_upstream_function_reuse(self):
        with isolated_copy() as root:
            imported = module('isolated_no_external_runtime', root)
            self.assertEqual(imported.sha((root / imported.UPSTREAM).read_bytes()), imported.UPSTREAM_SHA256)
            for name in ('run', 'verify', 'matches', 'classify', 'diagnostic_details'):
                self.assertIs(getattr(imported, name), getattr(imported.upstream, name))
            self.assertEqual(imported.upstream.ROOT, root.resolve())
            self.assertIs(imported.upstream.validate_pins, imported.validate_pins)
            self.assertEqual(len(imported.validate_pins()), len(imported.load(root / 'runtime-manifest.json')) +
                             len(imported.load(root / 'fixture-manifest.json')))

    def test_flat_manifests_preserve_candidate_and_only_prefix_case_paths(self):
        pins = v.validate_pins()
        self.assertIn('verify.sbatch', pins)
        snapshot = ROOT / 'inputs/candidate'
        self.assertEqual(v.sha((snapshot / 'candidate-manifest.json').read_bytes()), v.CANDIDATE_SHA256)
        original = v.load(snapshot / 'cases.json')
        current = v.load(ROOT / 'cases.json')
        self.assertEqual(current, [dict(c, path='inputs/candidate/' + c['path']) for c in original])
        self.assertEqual(len(current), 20)
        script = (ROOT / 'verify.sbatch').read_text()
        for required in ('#SBATCH --partition=test', '#SBATCH --no-requeue',
                         '#SBATCH --time=00:25:00', 'verify.py verification-001'):
            self.assertIn(required, script)

    def test_pin_validation_rejects_changed_extra_and_symlink_candidate_inputs(self):
        with isolated_copy() as root:
            name = v.load(root / 'cases.json')[0]['path'] + '/HelperA.dfy'
            source = root / name
            raw = source.read_bytes()
            source.write_bytes(raw + b'\n')
            with self.assertRaises(AssertionError):
                v.validate_pins(root)
            source.write_bytes(raw)
            extra = root / 'inputs/candidate/unpinned.txt'
            extra.write_text('must not be silently admitted')
            with self.assertRaisesRegex(AssertionError, 'inventory'):
                v.validate_pins(root)
            extra.unlink()
            source.unlink()
            source.symlink_to(root / 'inputs/candidate/README.md')
            with self.assertRaises(AssertionError):
                v.validate_pins(root)

    def test_case_diagnostics_remain_strict_and_frontend_is_not_proof(self):
        for case in v.load(ROOT / 'cases.json'):
            stdout, code = fake_result(case)
            record = dict(stdout=stdout.decode(), stderr='', exit_code=code)
            self.assertTrue(v.matches(case, record), case['case_id'])
        case = next(c for c in v.load(ROOT / 'cases.json') if c['expected'] == 'proof_failure')
        bad = dict(stdout='HelperA.dfy(1,1): Error: this symbol not expected in Dafny\n1 parse errors detected\n',
                   stderr='', exit_code=2)
        self.assertEqual(v.classify(bad), 'frontend_failure')
        self.assertFalse(v.matches(case, bad))
        good = dict(stdout='Dafny program verifier finished with 17 verified, 0 errors\n', stderr='', exit_code=0)
        self.assertEqual(v.classify(good), 'success')
        self.assertNotEqual(v.classify(dict(good, exit_code=2)), 'success')
        self.assertEqual(v.classify(dict(good, stderr='Warning: no trigger\n')), 'warning_only')

    def test_full_twenty_case_fake_run_preserves_exact_bytes_and_evidence(self):
        with isolated_copy() as root:
            cases = v.load(root / 'cases.json')
            calls = []
            verifier_cases = []
            raw_csv = b'Name,Outcome\r\nHelperA.Prove,FakeOnly\r\n'
            raw_stderr = b'offline fake process evidence \xff\r\n'

            def fake(command, **kwargs):
                calls.append(command)
                self.assertTrue(kwargs['capture_output'])
                if command in (['dafny', '--version'], ['z3', '--version']):
                    self.assertEqual(kwargs['timeout'], 15)
                    version = v.DAFNY_VERSION if command[0] == 'dafny' else v.Z3_VERSION
                    return types.SimpleNamespace(returncode=0, stdout=(version + '\n').encode(), stderr=b'')
                self.assertEqual(command, v.COMMAND)
                self.assertEqual(kwargs['timeout'], 75)
                case = cases[len(verifier_cases)]
                verifier_cases.append(case)
                folder = Path(kwargs['cwd'])
                actual = {p.name: p.read_bytes() for p in folder.glob('*.dfy')}
                expected = {p.name: p.read_bytes() for p in (root / case['path']).glob('*.dfy')}
                self.assertEqual(actual, expected)
                (folder / 'results.csv').write_bytes(raw_csv)
                stdout, code = fake_result(case)
                return types.SimpleNamespace(returncode=code, stdout=stdout, stderr=raw_stderr)

            with patch.object(v, 'ROOT', root), patch.object(v.upstream, 'ROOT', root), \
                 patch.dict(os.environ, {'SLURM_JOB_ID': 'OFFLINE-FAKE-NO-JOB', 'SLURM_JOB_PARTITION': 'offline-fake'}), \
                 patch.object(v.upstream.socket, 'gethostname', return_value='offline-fake-compute'), \
                 patch.object(v.upstream.shutil, 'which', return_value='/offline/fake/tool'), \
                 patch.object(v.upstream.subprocess, 'run', side_effect=fake), contextlib.redirect_stdout(io.StringIO()):
                self.assertTrue(v.run('verification-001'))
                with self.assertRaises(FileExistsError):
                    v.run('verification-001')
            self.assertEqual(len(calls), 22)  # Two fake version checks plus twenty fake verifiers.
            self.assertEqual(verifier_cases, cases)
            out = root / 'verification-001'
            summary = v.load(out / 'summary.json')
            self.assertEqual((summary['completed'], summary['planned'], summary['model_calls']), (20, 20, 0))
            self.assertTrue(summary['all_expected'])
            for case in cases:
                record = v.load(out / (case['case_id'] + '.json'))
                raw = out / 'raw' / case['case_id']
                self.assertEqual(record['source_sha256'], case['source_sha256'])
                self.assertEqual((record['attempts'], record['model_calls']), (1, 0))
                self.assertEqual(base64.b64decode(record['stderr_base64']), raw_stderr)
                self.assertEqual((raw / 'stderr.txt').read_bytes(), raw_stderr)
                self.assertEqual((raw / 'stdout.txt').read_bytes(), fake_result(case)[0])
                self.assertEqual((raw / 'csv/results.csv').read_bytes(), raw_csv)
                self.assertEqual(base64.b64decode(record['csv_base64']['results.csv']), raw_csv)
            for name, digest in v.validate_pins(root).items():
                self.assertEqual((out / name).read_bytes(), (root / name).read_bytes())
                self.assertEqual(v.sha((out / name).read_bytes()), digest)
            inventory = v.load(out / 'evidence-manifest.json')
            self.assertEqual(inventory, {p.relative_to(out).as_posix(): v.sha(p.read_bytes())
                                        for p in out.rglob('*') if p.is_file() and p.name != 'evidence-manifest.json'})

    def test_run_refuses_noncompute_or_unpinned_output_before_process(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(AssertionError, 'Compute allocation'):
                v.run('verification-001')
        with patch.dict(os.environ, {'SLURM_JOB_ID': 'OFFLINE-FAKE'}), \
             patch.object(v.upstream.socket, 'gethostname', return_value='holylogin-fake'):
            with self.assertRaisesRegex(AssertionError, 'Compute allocation'):
                v.run('verification-001')
        with patch.dict(os.environ, {'SLURM_JOB_ID': 'OFFLINE-FAKE'}), \
             patch.object(v.upstream.socket, 'gethostname', return_value='offline-fake-compute'):
            with self.assertRaisesRegex(AssertionError, 'one fresh'):
                v.run('verification-002')

    def test_one_fake_timeout_is_charged_as_one_attempt_without_retry(self):
        case = v.load(ROOT / 'cases.json')[0]
        files = {p.name: p.read_bytes() for p in (ROOT / case['path']).glob('*.dfy')}
        with patch.object(v.upstream.subprocess, 'run', side_effect=subprocess.TimeoutExpired(
                v.COMMAND, 75, output=b'partial stdout', stderr=b'partial stderr')) as fake:
            record = v.verify(files)
        self.assertEqual(fake.call_count, 1)
        self.assertEqual(record['attempts'], 1)
        self.assertEqual(record['model_calls'], 0)
        self.assertEqual(v.classify(record), 'timeout')
        self.assertFalse(v.matches(case, record))
        self.assertEqual(base64.b64decode(record['stdout_base64']), b'partial stdout')


if __name__ == '__main__':
    unittest.main(verbosity=2)
