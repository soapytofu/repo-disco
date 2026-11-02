"""Offline tests for the actual frozen proposal; no SDK, SSH or verifier calls."""
import collections
import json
import tempfile
import unittest
from pathlib import Path
import prepare as p

BUNDLE = p.ROOT / 'frozen-001'


class PlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tasks = p.load(BUNDLE / 'tasks.json')
        cls.grammar, cls.body = p.parser(BUNDLE)

    def test_reproducible_freeze_and_no_overwrite(self):
        p.validate_bundle(BUNDLE)
        with tempfile.TemporaryDirectory() as temp:
            other = p.prepare(Path(temp) / 'bundle')
            self.assertEqual(p.inventory(other), p.inventory(BUNDLE))
            with self.assertRaisesRegex(ValueError, 'overwrite'):
                p.prepare(other)
            (other / 'system.txt').write_text('changed')
            with self.assertRaisesRegex(ValueError, 'drift'):
                p.validate_bundle(other)

    def test_extra_missing_and_reordered_artifacts_are_detected(self):
        with tempfile.TemporaryDirectory() as temp:
            other = p.prepare(Path(temp) / 'bundle')
            extra = other / 'unexpected.txt'
            extra.write_text('unexpected')
            with self.assertRaises(ValueError):
                p.validate_bundle(other)
            extra.unlink()
            trials = p.load(other / 'trials.json')
            p.save(other / 'trials.json', list(reversed(trials)))
            with self.assertRaises(ValueError):
                p.validate_bundle(other)
            (other / 'system.txt').unlink()
            with self.assertRaises(ValueError):
                p.validate_bundle(other)

    def test_exact_parent_model_inputs_and_fresh_trial_identities(self):
        for name in ['system.txt', 'settings.json', 'tasks.json', 'order-design.json', 'preflight-gate.json']:
            self.assertEqual((BUNDLE / name).read_bytes(), (p.PARENT / name).read_bytes())
        for name in ['tasks', 'guard']:
            self.assertEqual(p.inventory(BUNDLE / name), p.inventory(p.PARENT / name))
        a = p.load(BUNDLE / 'trials.json')
        b = p.load(p.PARENT / 'trials.json')
        self.assertEqual(len(a), 32)
        self.assertFalse({t['trial_id'] for t in a} & {t['trial_id'] for t in b})
        for new, old in zip(a, b):
            self.assertEqual(new['source_trial_id'], old['trial_id'])
            self.assertEqual({k: v for k, v in new.items() if k not in ['trial_id', 'source_trial_id']},
                             {k: v for k, v in old.items() if k != 'trial_id'})
            self.assertEqual(new['prompt_sha256'], p.sha(BUNDLE / new['prompt_path']))
            self.assertEqual(new['system_sha256'], p.sha(BUNDLE / new['system_path']))
            self.assertTrue(new['fresh_context'])
            self.assertFalse(new['feedback'])

    def test_balance_and_reverse_order(self):
        trials = p.load(BUNDLE / 'trials.json')
        self.assertEqual(len({t['trial_id'] for t in trials}), 32)
        self.assertEqual(set(collections.Counter(t['task_id'] for t in trials).values()), {2})
        self.assertEqual(set(collections.Counter(t['family'] for t in trials).values()), {8})
        cells = {'shallow_shared', 'shallow_separate', 'deep_shared', 'deep_separate'}
        self.assertEqual(set(collections.Counter(t['cell'] for t in trials).values()), {8})
        self.assertEqual([t['task_id'] for t in trials[:16]], [t['task_id'] for t in trials[16:]][::-1])
        for sample in (1, 2):
            subset = [t for t in trials if t['sample'] == sample]
            self.assertEqual(len(subset), 16)
            for start in range(0, 16, 4):
                self.assertEqual({t['cell'] for t in subset[start:start + 4]}, cells)
                self.assertEqual(len({t['family'] for t in subset[start:start + 4]}), 4)
            for family in {t['family'] for t in subset}:
                self.assertEqual({t['cell'] for t in subset if t['family'] == family}, cells)

    def test_matched_clients_providers_and_helper_contracts(self):
        for family in {t['family'] for t in self.tasks}:
            tasks = [t for t in self.tasks if t['family'] == family]
            workspaces = [p.sources(BUNDLE / 'tasks' / t['task_id']) for t in tasks]
            for name in ['Kernel.dfy', 'Stage1.dfy', 'Stage2.dfy', 'Stage3.dfy', 'ClientA.dfy', 'ClientB.dfy', 'All.dfy']:
                self.assertEqual(len({s[name] for s in workspaces}), 1, (family, name))
            for name in ['HelperA.dfy', 'HelperB.dfy']:
                contracts = []
                for source in workspaces:
                    # Shared HelperB is an immutable nonempty forwarding body;
                    # the frozen output guard only splits EMPTY editable seeds.
                    # All reviewed templates use this exact body opening line.
                    self.assertEqual(source[name].count('\n  {\n'), 1)
                    prefix = source[name].split('\n  {\n', 1)[0]
                    contracts.append(prefix[prefix.index('  lemma '):])
                self.assertEqual(len(set(contracts)), 1, (family, name))
            for t in tasks:
                self.assertEqual(len(t['editable_files']), 1 if t['sharing'] == 'shared' else 2)

    def test_archived_evidence_reference_and_response_replays(self):
        audit = p.review_evidence()
        self.assertEqual(audit, p.load(BUNDLE / 'evidence-review.json'))
        self.assertEqual(sum(audit['selected_prior_controls'].values()), 136)
        self.assertEqual(audit['reference_replays'], 16)
        self.assertEqual(len(audit['smoke_replays']), 8)
        self.assertEqual(sum(r['verifier_exit'] == 0 for r in audit['smoke_replays']), 7)
        separate = [r for r in audit['smoke_replays'] if r['task_id'].endswith('-separate')]
        self.assertEqual(len(separate), 4)
        self.assertTrue(all(r['editable_bodies_identical'] for r in separate))

    def test_parser_does_not_repair_bad_syntax_or_allow_contract_bypass(self):
        for task in self.tasks:
            seed = p.sources(BUNDLE / 'tasks' / task['task_id'])
            for text in ['if true then assert true; else assert true;', 'assume false;',
                         'reveal K.Score();', 'assert {:axiom} false;', '} lemma Escape() {} {']:
                payload = json.dumps({n: text for n in task['editable_files']})
                with self.assertRaises(ValueError):
                    self.body.parse_response(payload, seed, task)
            valid = json.dumps({n: 'if true { assert true; } else { assert true; }' for n in task['editable_files']})
            self.body.parse_response(valid, seed, task)
            changed = dict(seed, **{'All.dfy': seed['All.dfy'] + '\n'})
            with self.assertRaisesRegex(ValueError, 'Seed hash'):
                self.body.parse_response(valid, changed, task)

    def test_interval_diagnostic_is_precondition_not_syntax_or_false_contract(self):
        failed = p.load(p.SMOKE / 'model-001/smoke-04/verification.json')
        self.assertEqual(failed['exit_code'], 4)
        self.assertIn('a precondition for this call could not be proved', failed['stdout'])
        self.assertIn('requires a <= w <= b', failed['stdout'])
        a, b, c, d = 2, 5, 0, 4
        self.assertTrue(a <= b and c <= d and a <= d and c <= b)
        self.assertFalse(a <= c <= b)
        w = max(a, c)
        self.assertTrue(a <= w <= b and c <= w <= d)
        finite = p.witness_arithmetic()
        self.assertGreater(finite['unconditional_c_failures'], 0)
        self.assertEqual(finite['branched_witness_failures'], 0)

    def test_preparation_is_not_execution_authorization(self):
        scope = p.load(BUNDLE / 'scope.json')
        self.assertEqual(scope['status'], 'FROZEN_PROPOSAL_NO_MODEL_AUTHORIZATION')
        self.assertEqual(scope['model_calls_made'], 0)
        self.assertEqual(scope['proposed_max_new_calls'], 32)
        self.assertEqual(scope['output_token_ceiling'], 131072)
        self.assertFalse(scope['automatic_retries'])
        self.assertFalse(scope['reassign_unused'])
        self.assertFalse(scope['pooling_with_prior_runs'])
        self.assertEqual(scope['sdk_total_max_attempts'], 1)
        self.assertEqual(scope['model_message_inputs_only'], ['system.txt', 'trial.prompt_path'])
        for name in ['authorization.json', 'run_pilot.py', 'model-001', 'submission.json', 'model.sbatch']:
            self.assertFalse((p.ROOT / name).exists())
        self.assertEqual((BUNDLE / 'difficulty-review.md').read_bytes(), (p.ROOT / 'DIFFICULTY_REVIEW.md').read_bytes())


if __name__ == '__main__':
    unittest.main(verbosity=2)
