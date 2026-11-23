"""Post-build integration checks on the four actual selected native observations.

These tests replay retained evidence only. They neither construct nor modify a
gate, and do not execute any verifier, transport, job, or model request.
"""
import json
from pathlib import Path
import unittest

import review

HERE = Path(__file__).resolve().parent
EXPERIMENT = HERE.parent
native = review.native
EXPECTED = {'stdlib-filter': 59, 'stdlib-splice': 60, 'aws-batch': 81, 'aws-tagged': 79}


def read_json(path):
    return json.loads(path.read_bytes())


class ActualReferenceGateTests(unittest.TestCase):
    def setUp(self):
        self.gate = read_json(HERE / 'reference-gate.json')

    def test_all_actual_receipts_replay_and_every_input_pin_matches(self):
        self.assertEqual(self.gate['status'], 'PASS')
        self.assertTrue(self.gate['all_references_match'])
        self.assertEqual(self.gate['model_calls'], 0)
        self.assertEqual(self.gate['new_native_calls'], 0)
        self.assertEqual(set(self.gate['tasks']), set(EXPECTED))
        self.assertFalse(self.gate['execution_release_issued'])
        for path, digest in self.gate['input_files'].items():
            self.assertTrue(native.safe_path(path), path)
            self.assertEqual(native.sha((EXPERIMENT / path).read_bytes()), digest, path)
        for task_id, task in self.gate['tasks'].items():
            with self.subTest(task=task_id):
                profile = read_json(EXPERIMENT / task['native_profile']['path'])
                record = read_json(EXPERIMENT / task['reference_record']['path'])
                report = read_json(EXPERIMENT / task['native_review']['path'])
                sources = {name: (EXPERIMENT / pin['path']).read_bytes()
                           for name, pin in task['reference_sources'].items()}
                raw = {name: (EXPERIMENT / pin['path']).read_bytes()
                       for name, pin in task['reference_raw'].items()}
                for pin in [task['native_profile'], task['native_review'], task['reference_record'],
                            task['edit_profile'], *task['reference_raw'].values(),
                            *task['reference_sources'].values(), *task['base_sources'].values()]:
                    self.assertEqual(native.sha((EXPERIMENT / pin['path']).read_bytes()), pin['sha256'])
                    self.assertEqual(task['input_files'][pin['path']], pin['sha256'])
                evidence = native.EvidencePins(task['native_profile']['canonical_sha256'],
                    task['reference_record']['canonical_sha256'],
                    native.sha(native.canonical(native.hashes(sources))),
                    tuple(sorted(native.hashes(raw).items())), task['native_run_id'], record['origin'])
                actual = native.review(profile, sources, record, raw, evidence)
                self.assertEqual(actual, report['replay'])
                self.assertEqual(actual['raw_fingerprint_sha256'], task['raw_fingerprint_sha256'])
                self.assertTrue(actual['qualified_success'])
                self.assertTrue(actual['strict_zero_warning_success'])
                self.assertTrue(actual['proof_coverage_complete'])
                self.assertTrue(actual['resources']['complete'])
                self.assertEqual(actual['resources']['exit_status'], 0)
                self.assertFalse(actual['synthetic'])
                self.assertFalse(actual['acceptance_issued'])
                self.assertEqual(task['named_units'], EXPECTED[task_id])
                self.assertEqual(len(profile['required_units']), EXPECTED[task_id])

    def test_actual_named_targets_unlogged_definitions_and_fixed_resources(self):
        for task_id, task in self.gate['tasks'].items():
            with self.subTest(task=task_id):
                profile = read_json(EXPERIMENT / task['native_profile']['path'])
                edit = read_json(EXPERIMENT / task['edit_profile']['path'])
                self.assertEqual(profile['project'], task_id)
                self.assertEqual(profile['stage'], 1)
                self.assertIsNone(edit['parent_requirement'])
                self.assertEqual(profile['verification_inputs'], edit['verification_inputs'])
                self.assertTrue(profile['actual_target_units'])
                for unit in profile['actual_target_units']:
                    self.assertEqual(profile['required_units'][unit], edit['addition']['path'])
                self.assertEqual(any('(correctness)' in unit for unit in profile['actual_target_units']),
                                 task_id.startswith('stdlib-'))
                for definition in profile['unlogged_definitions']:
                    self.assertFalse(definition['counted_as_pass'])
                    self.assertEqual(definition['source_sha256'], task['reference_sources'][definition['file']]['sha256'])
                    self.assertFalse(any(unit.startswith(definition['name'] + ' (')
                                         for unit in profile['required_units']))
                command = profile['command']
                self.assertEqual(command[command.index('--resource-limit') + 1],
                                 '1000000' if task_id.startswith('stdlib-') else '500000000')
                self.assertEqual(command[command.index('--cores') + 1], '1')

    def test_mixed_version_reuse_and_resource_failure_are_not_new_successes(self):
        filter_task = self.gate['tasks']['stdlib-filter']
        self.assertEqual(filter_task['reference_case_id'], 'filter-reference')
        self.assertEqual(filter_task['fixture_binding']['observed_manifest'], 'stdlib/revision-003/manifest.json')
        self.assertEqual(filter_task['fixture_binding']['selected_manifest'], 'stdlib/revision-004/manifest.json')
        self.assertTrue(filter_task['fixture_binding']['observation_reused_across_fixture_paths'])
        self.assertEqual(filter_task['fixture_binding']['new_native_observations'], 0)
        self.assertEqual(self.gate['tasks']['stdlib-splice']['reference_case_id'], 'splice-alternative')
        excluded = [row for row in self.gate['excluded_analyst_observations']
                    if row['path'].startswith('qualification-005/')]
        self.assertEqual(len(excluded), 1)
        row = excluded[0]
        self.assertFalse(row['eligible_model_parent'])
        self.assertNotEqual(row['exit_code'], 0)
        self.assertIn(row['run_id'], self.gate['ineligible_parent_runs'])
        self.assertIn(row['raw_fingerprint_sha256'], self.gate['ineligible_parent_raw_fingerprints'])
        self.assertNotIn(row['run_id'], {task['native_run_id'] for task in self.gate['tasks'].values()})
        decision = read_json(HERE / 'selection-004.json')['solvability_selection_decision']
        self.assertFalse(decision['source_or_contract_change'])
        self.assertFalse(decision['resource_escalation'])
        self.assertEqual(decision['model_calls_at_selection'], 0)
        self.assertEqual(decision['current_matrix_if_reference_gate_passes']['selected_positive_cases'], 4)
        self.assertEqual(decision['current_matrix_if_reference_gate_passes']['distinct_remaining_controls'], 26)
        self.assertEqual(decision['current_matrix_if_reference_gate_passes']['constructed_fixture_cases'], 31)


if __name__ == '__main__':
    unittest.main(verbosity=2)
