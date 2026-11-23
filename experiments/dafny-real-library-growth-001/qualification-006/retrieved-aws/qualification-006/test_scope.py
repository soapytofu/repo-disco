"""Offline control-scope and capture-boundary tests; no native verifier calls."""
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
CONTROL_IDS = ['stage1-always-failure', 'stage1-wrong-suffix', 'stage1-wrong-payload',
    'stage2-always-failure', 'stage2-swapped-fields', 'stage2-wrong-suffix',
    'stage2-missing-second-frame', 'unproved-parent-reference-child',
    'stage2-omitted-from-roots']
BASE = ['StandardLibrary/src/UInt.dfy', 'libraries/src/BoundedInts.dfy',
        'libraries/src/Wrappers.dfy']
FIRST = 'StandardLibrary/src/RepoDiscoU16Frame.dfy'
SECOND = 'StandardLibrary/src/RepoDiscoFramePair.dfy'


def read(path):
    return json.loads(path.read_bytes())


class ScopeTests(unittest.TestCase):
    def test_exact_nine_control_projection_no_positive_dispatch(self):
        config = read(HERE / 'configs/aws.json')
        cases = read(REVISION / 'cases.json')
        self.assertEqual([c['id'] for c in config['cases']], CONTROL_IDS)
        self.assertEqual(len(cases), 12)
        self.assertEqual(sum(len(c['source_sha256']) for c in cases), 54)
        for actual, source in zip(config['cases'], cases[3:]):
            self.assertEqual(actual, {k: ('aws/revision-002/' + source[k]
                if k == 'workspace_dir' else source[k])
                for k in ('command_files', 'id', 'source_sha256', 'workspace_dir')})
            expected_files = BASE + [FIRST]
            if source['stage'] == 2 and not source['omit_from_command']:
                expected_files += [SECOND]
            self.assertEqual(actual['command_files'], expected_files)
            self.assertEqual([config['dafny'], 'verify'] + config['options']
                             + actual['command_files'], source['argv'])
        self.assertTrue(set(POSITIVES).isdisjoint(CONTROL_IDS))
        self.assertEqual(sorted(p.stem for p in (HERE / 'configs').glob('*.json')), ['aws'])
        with self.assertRaises(FileNotFoundError):
            ops.identity('stdlib')

    def test_all_source_cases_and_reference_gate_are_exact_pinned_inputs(self):
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
        binding = read(HERE / 'reference-gate-binding.json')
        gate = PACKAGE / binding['path']
        self.assertEqual(collect.sha(gate.read_bytes()), binding['sha256'])
        self.assertEqual(freeze['files'][binding['path']], binding['sha256'])
        self.assertEqual(binding['reference_case_ids'], POSITIVES)
        self.assertEqual(binding['source_manifest_sha256'],
                         collect.sha((REVISION / 'manifest.json').read_bytes()))
        self.assertTrue(binding['review_passed'])
        review = read(gate)
        self.assertEqual(review['schema'], 'repodisco-aws-reference-gate-v1')
        self.assertEqual(review['status'], 'PASS_REFERENCE_ONLY')
        self.assertEqual(review['project'], 'aws')
        self.assertEqual(review['counts'], {'total_expected': 3, 'total_matching': 3})
        self.assertTrue(review['native_inventory_complete'])
        self.assertTrue(review['all_positive_expectations_match'])
        self.assertEqual(review['controls_authorized'], CONTROL_IDS)
        self.assertEqual(review['expected_control_categories'],
                         {'COVERAGE_OMISSION': 1, 'PROOF_FAILURE': 8})
        self.assertEqual([o['case_id'] for o in review['observations']], POSITIVES)
        self.assertEqual([o['named_units'] for o in review['observations']], [71, 75, 77])
        for observation in review['observations']:
            self.assertTrue(observation['expected_match'])
            self.assertEqual(observation['category'], 'PROOF_PASS')
            self.assertEqual(observation['exit_code'], 0)
            self.assertFalse(observation['timeout'])
            self.assertEqual(observation['warning_count'], 0)
            self.assertEqual(len(observation['exact_units']), observation['named_units'])
        self.assertIn('RepoDiscoU16Frame.ReadU16Frame (well-formedness)',
                      review['observations'][1]['exact_units'])
        self.assertIn('RepoDiscoFramePair.ReadFramePair (well-formedness)',
                      review['observations'][2]['exact_units'])
        for name, digest in review['input_files'].items():
            self.assertEqual(collect.sha((PACKAGE / name).read_bytes()), digest)
            self.assertEqual(freeze['files'][name], digest)

    def test_expectations_preserve_omission_and_unproved_parent_semantics(self):
        original = read(REVISION / 'cases.json')[3:]
        retained = read(HERE / 'controls.json')
        self.assertEqual(retained['cases'], original)
        self.assertEqual(retained['origin_sha256'], collect.sha((REVISION / 'cases.json').read_bytes()))
        self.assertEqual(sum(c['expected_category'] == 'PROOF_FAILURE' for c in original), 8)
        self.assertEqual(sum(c['expected_category'] == 'COVERAGE_OMISSION' for c in original), 1)
        omission = original[-1]
        self.assertEqual(omission['expected_native_category'], 'PROOF_PASS')
        self.assertIn(SECOND, omission['source_sha256'])
        self.assertNotIn(SECOND, omission['command_files'])
        self.assertEqual(omission['omitted_targets'], ['RepoDiscoFramePair.ReadFramePair'])
        self.assertEqual(omission['required_targets'],
                         ['RepoDiscoU16Frame.ReadU16Frame', 'RepoDiscoFramePair.ReadFramePair'])
        wrong = original[3]
        self.assertEqual(omission['source_sha256'][SECOND], wrong['source_sha256'][SECOND])
        parent = original[-2]
        self.assertEqual(parent['expected_failed_targets'], ['RepoDiscoU16Frame.ReadU16Frame'])
        self.assertEqual(parent['inspect_targets'], ['RepoDiscoFramePair.ReadFramePair'])
        self.assertFalse(parent['child_outcome_predetermined'])
        self.assertEqual(parent['expected_passed_targets'], [])
        reference = read(REVISION / 'cases.json')[2]
        self.assertEqual(parent['source_sha256'][SECOND], reference['source_sha256'][SECOND])
        self.assertFalse(retained['new_native_correctness_labels_invented'])

    def test_prior_policy_and_code_origins_exactly_retained(self):
        history = HERE / 'history/qualification-005'
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
            expected = prior_bytes.replace(b'qualification-005', b'qualification-006')
            expected = expected.replace(b'libq005-', b'libq006-')
            self.assertEqual((HERE / name).read_bytes(), expected)
            self.assertEqual(collect.sha(prior_bytes), provenance['origins'][name]['origin_sha256'])
            self.assertEqual(collect.sha(expected), provenance['origins'][name]['current_sha256'])
        self.assertEqual((HERE / 'collect.py').read_bytes(), (history / 'collect.py').read_bytes())
        script = (HERE / 'run.sbatch').read_text()
        for directive in ('--cpus-per-task=1', '--mem=4G', '--time=01:00:00',
                          '--partition=test', '--no-requeue'):
            self.assertIn('#SBATCH ' + directive, script)

    def run_fake_controls(self, stop_index=None):
        config = copy.deepcopy(read(HERE / 'configs/aws.json'))
        cases = read(REVISION / 'cases.json')
        invocations = []
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp).resolve()
            q = package / 'qualification-006'
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
                self.assertEqual(cwd.parent.name, CONTROL_IDS[index])
                Path(argv[3]).write_text('explicit synthetic resources; not a measurement\n')
                stream_paths[0].write_bytes(b'explicit synthetic stdout; not verification\n')
                stream_paths[1].write_bytes(b'')
                (cwd / 'synthetic.csv').write_bytes(b'explicit synthetic; not proof evidence\n')
                timed = index == stop_index
                code = -15 if timed else (4 if index < 8 else 0)
                return dict(exit_code=code, elapsed_seconds=0.001, timeout=timed), \
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
            expected_count = 9 if stop_index is None else stop_index + 1
            self.assertEqual(summary['native_calls'], expected_count)  # Mocked attempts only.
            self.assertEqual(summary['model_calls'], 0)
            self.assertEqual(summary['all_planned_cases_recorded'], stop_index is None)
            self.assertEqual([c['case'] for c in summary['cases']], CONTROL_IDS[:expected_count])
            self.assertEqual(len(invocations), expected_count)
            self.assertEqual([c['exit_code'] for c in summary['cases']],
                             [4] * 8 + [0] if stop_index is None else [4] * stop_index + [-15])
            for case in config['cases'][:expected_count]:
                record = read(output / case['id'] / 'record.json')
                self.assertEqual(record['source_before_sha256'], case['source_sha256'])
                self.assertEqual(record['source_after_sha256'], case['source_sha256'])
                self.assertEqual(record['attempts'], 1)
                self.assertIn('csv/synthetic.csv', record['raw_sha256'])
            self.assertTrue(all(not (output / c['id']).exists()
                                for c in config['cases'][expected_count:]))
            self.assertTrue(all(not (output / name).exists() for name in POSITIVES))

    def test_actual_collector_preserves_nine_mocked_outcomes_without_retry(self):
        self.run_fake_controls()

    def test_timeout_preserves_prefix_and_leaves_tail_undispatched(self):
        self.run_fake_controls(stop_index=1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
