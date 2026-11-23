"""Offline regression for the Slurm submission-directory failure.

No SSH, scheduler, verifier or provider is contacted. Production submission code
is executed with a fail-closed fake subprocess; the shell script is exercised
with only its exact Conda-prefix assignment redirected to a temporary fake
Python executable. Collector/config/source bytes are not executed or modified.
"""
import contextlib
import io
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import collect
import ops


HERE = Path(__file__).resolve().parent
CONDA_LINE = 'export CONDA_PREFIX=/n/home13/sophiezeng/.conda/envs/repodisco'


class SubmissionTests(unittest.TestCase):
    def synthetic_package(self, base, project):
        package = base / 'runtime root'
        package.mkdir()
        q = package / 'qualification-005'
        (q / 'freezes').mkdir(parents=True)
        source = package / 'synthetic-input.txt'
        source.write_bytes(b'explicit synthetic offline input\n')
        freeze = dict(schema='dafny-library-qualification-freeze-v1',
                      project=project,
                      files={'synthetic-input.txt': ops.sha(source.read_bytes())})
        raw = ops.encode(freeze)
        (q / 'freezes' / (project + '.json')).write_bytes(raw)
        return package, q, ops.sha(raw)

    def submit_with_fake_scheduler(self, base, project, mutate_freeze=False):
        root, remote_q, expected = self.synthetic_package(base, project)
        local = base / 'local'
        (local / 'preflight').mkdir(parents=True)
        (local / 'preflight' / (project + '.json')).write_bytes(b'{"exit_code":0}')
        calls = []

        def fake_run(argv, **kwargs):
            calls.append((argv, kwargs))
            if argv[0] == 'squeue':
                self.assertEqual(kwargs['timeout'], 15)
                return subprocess.CompletedProcess(argv, 0, '', '')
            if argv == ['scontrol', 'show', 'partition', 'test']:
                return subprocess.CompletedProcess(
                    argv, 0, 'PartitionName=test PreemptMode=OFF State=UP MaxTime=12:00:00', '')
            if argv[0] == 'sbatch':
                self.assertEqual(kwargs['cwd'], root)
                self.assertEqual(kwargs['timeout'], 30)
                self.assertIn('--chdir=' + str(root), argv)
                self.assertIn('--export=ALL,REPODISCO_FREEZE_SHA=' + expected
                              + ',REPODISCO_EXECUTION_ROOT=' + str(root), argv)
                self.assertEqual(argv[-2:], [str(remote_q / 'run.sbatch'), project])
                self.assertIn('--job-name=libq005-' + project, argv)
                return subprocess.CompletedProcess(argv, 0, '12345678\n', '')
            raise AssertionError('Unmocked subprocess: ' + repr(argv))

        def fake_remote(actual_project, code, data=None, seconds=45):
            self.assertEqual(actual_project, project)
            self.assertEqual(seconds, 60)
            self.assertIsNone(data)
            if mutate_freeze:
                path = remote_q / 'freezes' / (project + '.json')
                path.write_bytes(path.read_bytes() + b' ')
            out = io.StringIO()
            with contextlib.redirect_stdout(out), mock.patch.object(subprocess, 'run', fake_run):
                exec(compile(code, '<actual ops.submit remote program>', 'exec'),
                     {'root': root, 'EXPECTED_FREEZE': expected})
            return out.getvalue().encode()

        with mock.patch.object(ops, 'ROOT', local), mock.patch.object(ops, 'remote', fake_remote), \
                contextlib.redirect_stdout(io.StringIO()):
            if mutate_freeze:
                with self.assertRaisesRegex(AssertionError, 'authoritative local pin'):
                    ops.submit(project)
            else:
                ops.submit(project)
        return root, calls

    def test_real_submit_program_cwd_export_and_versioned_paths(self):
        for project in ('stdlib', 'aws'):
            with self.subTest(project=project), tempfile.TemporaryDirectory() as tmp:
                root, calls = self.submit_with_fake_scheduler(Path(tmp), project)
                self.assertEqual([x[0][0] for x in calls], ['squeue', 'scontrol', 'sbatch'])
                self.assertTrue((root / 'submission.intent.json').is_file())
                self.assertEqual(json.loads((root / 'submission.json').read_bytes())['exit_code'], 0)

    def test_changed_remote_freeze_prevents_scheduler_and_intent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, calls = self.submit_with_fake_scheduler(Path(tmp), 'stdlib', mutate_freeze=True)
            self.assertEqual(calls, [])
            self.assertFalse((root / 'submission.intent.json').exists())

    def test_remote_prefix_uses_authoritative_local_digest_and_qualified_python(self):
        with tempfile.TemporaryDirectory() as tmp:
            package, q, expected = self.synthetic_package(Path(tmp), 'stdlib')
            calls = []

            def fake_ssh(argv, **kwargs):
                calls.append((argv, kwargs))
                self.assertEqual(argv[0], 'ssh')
                remote_args = shlex.split(argv[-1])
                self.assertEqual(remote_args[:3], [ops.PYTHON, '-B', '-c'])
                self.assertIn('EXPECTED_FREEZE=' + repr(expected), remote_args[3])
                self.assertIn('outputs/dafny-real-library-growth-001/qualification-005/stdlib', remote_args[3])
                self.assertEqual(kwargs['timeout'], 45)
                return subprocess.CompletedProcess(argv, 0, b'synthetic', b'')

            with mock.patch.object(ops, 'ROOT', q), mock.patch.object(ops, 'PACKAGE', package), \
                    mock.patch.object(subprocess, 'run', fake_ssh):
                self.assertEqual(ops.remote('stdlib', 'pass\n'), b'synthetic')
            self.assertEqual(len(calls), 1)

    def run_fake_shell(self, base, project, missing=None):
        root = base / 'runtime root'
        q = root / 'qualification-005'
        (q / 'configs').mkdir(parents=True)
        (q / 'configs' / (project + '.json')).write_text('{}\n')
        (q / 'collect.py').write_text('raise AssertionError("Must never execute collector")\n')
        fake_conda = base / 'fake-conda'
        (fake_conda / 'bin').mkdir(parents=True)
        fake_python = fake_conda / 'bin/python'
        fake_python.write_text('#!' + sys.executable + '\n'
            'import json,os,sys\n'
            'from pathlib import Path\n'
            'with open(os.environ["SYNTHETIC_CAPTURE"],"x") as f:\n'
            ' json.dump(dict(cwd=os.getcwd(),args=sys.argv[1:],'
            'root=os.environ.get("REPODISCO_EXECUTION_ROOT"),'
            'freeze=os.environ.get("REPODISCO_FREEZE_SHA"),'
            'config_exists=Path(sys.argv[4]).is_file()),f)\n')
        fake_python.chmod(0o700)
        text = (HERE / 'run.sbatch').read_text()
        self.assertEqual(text.count(CONDA_LINE), 1)
        text = text.replace(CONDA_LINE, 'export CONDA_PREFIX=' + shlex.quote(str(fake_conda)), 1)
        script = base / 'synthetic-run.sbatch'
        script.write_text(text)
        wrong_home = base / 'wrong-submit-home'
        wrong_home.mkdir()
        receipt = base / 'synthetic-invocation.json'
        env = dict(os.environ, SLURM_SUBMIT_DIR=str(wrong_home),
                   REPODISCO_EXECUTION_ROOT=str(root), REPODISCO_FREEZE_SHA='a' * 64,
                   SYNTHETIC_CAPTURE=str(receipt))
        if missing:
            env.pop(missing)
        result = subprocess.run(['/bin/bash', str(script), project], cwd=wrong_home,
                                env=env, capture_output=True, text=True, timeout=10)
        return root, receipt, result

    def test_shell_ignores_wrong_submit_dir_and_forwards_config_freeze(self):
        for project in ('stdlib', 'aws'):
            with self.subTest(project=project), tempfile.TemporaryDirectory() as tmp:
                root, receipt, result = self.run_fake_shell(Path(tmp), project)
                self.assertEqual(result.returncode, 0, result.stderr)
                actual = json.loads(receipt.read_bytes())
                self.assertEqual(Path(actual['cwd']).resolve(), root.resolve())
                self.assertEqual(actual['root'], str(root))
                self.assertEqual(actual['freeze'], 'a' * 64)
                self.assertEqual(actual['args'], ['-B', '-u', 'qualification-005/collect.py',
                    'qualification-005/configs/' + project + '.json',
                    'qualification-005/output-' + project, '--expected-freeze-sha', 'a' * 64])
                self.assertTrue(actual['config_exists'])

    def test_missing_root_or_freeze_fails_before_python(self):
        for missing in ('REPODISCO_EXECUTION_ROOT', 'REPODISCO_FREEZE_SHA'):
            with self.subTest(missing=missing), tempfile.TemporaryDirectory() as tmp:
                _, receipt, result = self.run_fake_shell(Path(tmp), 'stdlib', missing)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(receipt.exists())
                self.assertIn('Missing ', result.stderr)

    def test_collector_rejects_changed_freeze_before_output_or_native(self):
        with tempfile.TemporaryDirectory() as tmp:
            package, q, expected = self.synthetic_package(Path(tmp), 'stdlib')
            config = q / 'config.json'
            config.write_text(json.dumps(dict(schema='dafny-library-qualification-v1',
                                              freeze='freezes/stdlib.json')))
            freeze_path = q / 'freezes/stdlib.json'
            freeze_path.write_bytes(freeze_path.read_bytes() + b' ')
            output = q / 'output-stdlib'
            with mock.patch.object(collect, 'ROOT', q), \
                    mock.patch.dict(os.environ, {'SLURM_JOB_ID': 'synthetic', 'SLURM_CPUS_PER_TASK': '1'}), \
                    mock.patch.object(collect.socket, 'gethostname', return_value='synthetic-compute'), \
                    mock.patch.object(collect, 'capture', side_effect=AssertionError('Native call forbidden')) as capture:
                with self.assertRaises(AssertionError):
                    collect.run(config, output, expected)
            capture.assert_not_called()
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
