"""Offline scope/provenance and fake-collector tests for qualification 005.

All native calls are mocked. Synthetic logs below are never proof evidence.
"""
import copy
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import collect
import ops


HERE = Path(__file__).resolve().parent
PACKAGE = HERE.parent
REVISION = PACKAGE / 'aws/revision-002'
POSITIVES = ['baseline', 'stage1-reference', 'stage2-reference']
BASE = ['StandardLibrary/src/UInt.dfy', 'libraries/src/BoundedInts.dfy',
        'libraries/src/Wrappers.dfy']
FIRST = 'StandardLibrary/src/RepoDiscoU16Frame.dfy'
SECOND = 'StandardLibrary/src/RepoDiscoFramePair.dfy'


def read(path):
    return json.loads(path.read_bytes())


class ScopeTests(unittest.TestCase):
    def test_exact_three_positive_projection_no_control_dispatch(self):
        config = read(HERE / 'configs/aws.json')
        cases = read(REVISION / 'cases.json')
        self.assertEqual([c['id'] for c in config['cases']], POSITIVES)
        self.assertEqual(len(cases), 12)
        self.assertEqual(sum(len(c['source_sha256']) for c in cases), 54)
        for actual, source, expected_files in zip(config['cases'], cases[:3],
                [BASE, BASE + [FIRST], BASE + [FIRST, SECOND]]):
            self.assertEqual(actual, {k: ('aws/revision-002/' + source[k]
                if k == 'workspace_dir' else source[k])
                for k in ('command_files', 'id', 'source_sha256', 'workspace_dir')})
            self.assertEqual(actual['command_files'], expected_files)
            self.assertEqual(set(actual['source_sha256']), set(expected_files))
            self.assertEqual([config['dafny'], 'verify'] + config['options']
                             + actual['command_files'], source['argv'])
        self.assertTrue(all(c['gated_until_positive_review'] for c in cases[3:]))
        self.assertTrue(set(c['id'] for c in cases[3:]).isdisjoint(POSITIVES))
        self.assertEqual(sorted(p.stem for p in (HERE / 'configs').glob('*.json')), ['aws'])
        with self.assertRaises(FileNotFoundError):
            ops.identity('stdlib')

    def test_all_twelve_source_cases_are_exact_pinned_inputs(self):
        _, freeze = ops.identity('aws')
        manifest = read(REVISION / 'manifest.json')
        self.assertEqual(collect.sha((REVISION / 'manifest.json').read_bytes()),
            '3e295673e59973a47ae11d9c947726e949f4531f9897644ee9bd6dafac217bb4')
        for name, digest in manifest['files'].items():
            self.assertEqual(freeze['files']['aws/revision-002/' + name], digest)
        for case in read(REVISION / 'cases.json'):
            actual = collect.sources(REVISION / case['workspace_dir'])
            self.assertEqual(actual, case['source_sha256'])
            for name, digest in actual.items():
                full = 'aws/revision-002/' + case['workspace_dir'] + '/' + name
                self.assertEqual(freeze['files'][full], digest)
        omitted = read(REVISION / 'cases.json')[-1]
        self.assertEqual(omitted['id'], 'stage2-omitted-from-roots')
        self.assertIn(SECOND, omitted['source_sha256'])
        self.assertNotIn(SECOND, omitted['command_files'])
        self.assertNotIn(omitted['id'], [c['id'] for c in read(HERE / 'configs/aws.json')['cases']])

    def test_prior_policy_and_code_origins_exactly_retained(self):
        history = HERE / 'history/qualification-004'
        prior = read(history / 'configs/aws.json')
        current = read(HERE / 'configs/aws.json')
        self.assertEqual({k: v for k, v in current.items() if k != 'cases'},
                         {k: v for k, v in prior.items() if k != 'cases'})
        self.assertEqual(current['wall_seconds'], 900)
        options = current['options']
        for flag, value in [('--cores', '1'), ('--verification-time-limit', '300'),
                            ('--resource-limit', '500000000')]:
            self.assertEqual(options[options.index(flag) + 1], value)
        self.assertIn('--enforce-determinism', options)
        self.assertEqual(current['expected_tool_fingerprint']['solver_sha256'],
                         'b14068b578fe6f2ad90d46183ba73b1c4ee071de8caccc455b9fcc6d3eb1d320')
        provenance = read(HERE / 'copy-provenance.json')
        for name in ('collect.py', 'ops.py', 'run.sbatch', 'test_capture.py',
                     'test_submission.py', 'test_version.py'):
            prior_bytes = (history / name).read_bytes()
            expected = prior_bytes.replace(b'qualification-004', b'qualification-005')
            if name in ('ops.py', 'test_submission.py'):
                expected = expected.replace(b'libq-', b'libq005-')
            self.assertEqual((HERE / name).read_bytes(), expected)
            self.assertEqual(collect.sha(prior_bytes), provenance['origins'][name]['origin_sha256'])
            self.assertEqual(collect.sha(expected), provenance['origins'][name]['current_sha256'])
        self.assertEqual((HERE / 'collect.py').read_bytes(), (history / 'collect.py').read_bytes())
        script = (HERE / 'run.sbatch').read_text()
        for directive in ('--cpus-per-task=1', '--mem=4G', '--time=01:00:00',
                          '--partition=test', '--no-requeue'):
            self.assertIn('#SBATCH ' + directive, script)

    def test_actual_collector_runs_only_three_configured_cases_with_fake_capture(self):
        config = copy.deepcopy(read(HERE / 'configs/aws.json'))
        cases = read(REVISION / 'cases.json')
        invocations = []
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp).resolve()
            q = package / 'qualification-005'
            (q / 'configs').mkdir(parents=True)
            (q / 'freezes').mkdir()
            for case in cases:
                target = package / 'aws/revision-002' / case['workspace_dir']
                shutil.copytree(REVISION / case['workspace_dir'], target)
            executable = package / 'never-execute-this-synthetic-tool'
            executable.write_text('Explicit synthetic test sentinel; never executed.\n')
            config['dafny'] = str(executable)
            config_path = q / 'configs/aws.json'
            config_path.write_bytes(ops.encode(config))
            pins = {p.relative_to(package).as_posix(): collect.sha(p.read_bytes())
                    for p in package.rglob('*') if p.is_file()}
            freeze_path = q / 'freezes/aws.json'
            freeze_path.write_bytes(ops.encode(dict(schema='dafny-library-qualification-freeze-v1',
                                                    files=pins, explicit_synthetic=True)))

            def fake_version(exe, flag, out, label):
                self.assertEqual(flag, '--version' if label == 'tool' else '-version')
                return config['expected_version'] if label == 'tool' else 'Z3 synthetic'

            def fake_capture(argv, cwd, seconds, stream_paths):
                invocations.append((argv, cwd, seconds))
                index = len(invocations) - 1
                case = config['cases'][index]
                self.assertEqual(seconds, 900)
                self.assertEqual(argv[:3], ['/usr/bin/time', '-v', '-o'])
                self.assertEqual(argv[4:], [str(executable), 'verify'] + config['options']
                                 + case['command_files'])
                self.assertEqual(cwd.parent.name, POSITIVES[index])
                Path(argv[3]).write_text('explicit synthetic resources; not a measurement\n')
                stream_paths[0].write_bytes(b'explicit synthetic stdout; not verification\n')
                stream_paths[1].write_bytes(b'')
                (cwd / 'synthetic.csv').write_bytes(b'explicit synthetic; not proof evidence\n')
                return dict(exit_code=0, elapsed_seconds=0.001, timeout=False), \
                    stream_paths[0].read_bytes(), stream_paths[1].read_bytes()

            output = q / 'output-aws'
            with patch.object(collect, 'ROOT', q), \
                    patch.dict(os.environ, {'SLURM_JOB_ID': 'synthetic', 'SLURM_CPUS_PER_TASK': '1'}), \
                    patch.object(collect.socket, 'gethostname', return_value='synthetic-compute'), \
                    patch.object(collect, 'tool_fingerprint', return_value=config['expected_tool_fingerprint']), \
                    patch.object(collect, 'capture_version', side_effect=fake_version), \
                    patch.object(collect, 'capture', side_effect=fake_capture):
                collect.run(config_path, output, collect.sha(freeze_path.read_bytes()))
            summary = read(output / 'summary.json')
            self.assertEqual(summary['native_calls'], 3)  # Three mocked attempts, no actual native process.
            self.assertEqual(summary['model_calls'], 0)
            self.assertTrue(summary['all_planned_cases_recorded'])
            self.assertEqual([c['case'] for c in summary['cases']], POSITIVES)
            self.assertEqual(len(invocations), 3)
            for case in config['cases']:
                record = read(output / case['id'] / 'record.json')
                self.assertEqual(record['source_before_sha256'], case['source_sha256'])
                self.assertEqual(record['source_after_sha256'], case['source_sha256'])
                self.assertEqual(record['attempts'], 1)
                self.assertIn('csv/synthetic.csv', record['raw_sha256'])
            self.assertTrue(all(not (output / c['id']).exists() for c in cases[3:]))


if __name__ == '__main__':
    unittest.main(verbosity=2)
