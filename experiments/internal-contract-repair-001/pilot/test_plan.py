"""Focused local prompt-freeze checks. No verifier, provider or network use."""
from collections import Counter
from pathlib import Path
import base64
import copy
import importlib.util
import json
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('internal_method_prompt_preparation', HERE / 'prepare.py')
prep = importlib.util.module_from_spec(spec); spec.loader.exec_module(prep)


class PromptFreezeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output, cls.pins = prep.contents()
        cls.plan, cls.tasks, cls.records, cls.gate, cls.policy, cls.measurement, _ = prep.source_inputs()
        cls.parents = json.loads(cls.output['parents.json'])

    def payloads(self):
        return {name: json.loads(raw) for name, raw in self.output.items() if name.startswith('requests/')}

    def test_four_exact_converse_payloads_and_readable_prompts(self):
        payloads = self.payloads(); self.assertEqual(len(payloads), 4)
        self.assertEqual(len({prep.sha(self.output[name]) for name in payloads}), 4)
        for name, payload in payloads.items():
            self.assertEqual(set(payload), {'modelId', 'system', 'messages', 'inferenceConfig'})
            self.assertEqual(payload['modelId'], self.plan['model_id'])
            self.assertEqual(payload['inferenceConfig'], self.plan['inference_config'])
            self.assertEqual(payload['system'], [{'text': self.output['system.txt'].decode()}])
            self.assertEqual(len(payload['messages']), 1)
            self.assertEqual(payload['messages'][0]['role'], 'user')
            self.assertEqual(len(payload['messages'][0]['content']), 1)
            user = payload['messages'][0]['content'][0]['text']
            readable = 'prompts/' + Path(name).stem + '.txt'
            self.assertEqual(self.output[readable].decode(), 'SYSTEM\n' + payload['system'][0]['text'] + '\nUSER\n' + user)
            self.assertIn('without the outer method braces', user)
            self.assertIn('Either body may remain unchanged', user)
            self.assertIn('Calling H.Transfer is permitted but not required.', user)
            self.assertIn('never a typed local declaration', user)
            self.assertIn('entire right-hand side', user)

    def test_full_seed_source_and_fixed_interfaces_are_exact(self):
        for task in self.tasks:
            parent = self.parents[task['task_id']]
            source = {n: self.output[parent['base_path'] + '/' + n] for n in prep.FILES}
            self.assertEqual({n: prep.sha(b) for n, b in source.items()}, task['source_sha256'])
            helper_start = task['body_boundaries']['Helper.dfy']['start']
            client_start = task['body_boundaries']['Client.dfy']['start']
            self.assertEqual(source['Helper.dfy'][:helper_start], task['fixed_helper_prefix'].encode())
            self.assertEqual(source['Client.dfy'][:client_start], task['public_contract_prefix'].encode())
            for arm in ('diagnostics', 'notice'):
                payload = json.loads(self.output['requests/' + parent['workspace_id'] + '-' + arm + '.json'])
                text = payload['messages'][0]['content'][0]['text']
                for name, raw in source.items():
                    section = 'FILE ' + name + '\n```dafny\n' + raw.decode() + '```'
                    self.assertEqual(text.count(section), 1)
            frozen_task = json.loads(self.output[parent['task_path']])
            self.assertEqual(frozen_task['file_rules'], task['file_rules'])
            self.assertNotIn('counterexamples', frozen_task)

    def test_only_feedback_differs_between_paired_arms(self):
        for parent in self.parents.values():
            prefix = 'requests/' + parent['workspace_id']
            diag = json.loads(self.output[prefix + '-diagnostics.json'])
            notice = json.loads(self.output[prefix + '-notice.json'])
            dtext, ntext = (p['messages'][0]['content'][0]['text'] for p in (diag, notice))
            self.assertEqual(prep.without_feedback(dtext), prep.without_feedback(ntext))
            self.assertIn(prep.OPEN + prep.NOTICE + prep.CLOSE, ntext)
            expected_feedback = json.dumps(json.loads(self.output[parent['feedback_path']]), indent=2)
            self.assertIn(prep.OPEN + expected_feedback + prep.CLOSE, dtext)
            diag['messages'][0]['content'][0]['text'] = prep.without_feedback(dtext)
            notice['messages'][0]['content'][0]['text'] = prep.without_feedback(ntext)
            self.assertEqual(diag, notice)

    def test_exact_balanced_sixteen_slot_order_and_disabled_execution(self):
        order = json.loads(self.output['order.json'])
        self.assertEqual([{k: trial[k] for k in original} for trial, original in zip(order, self.plan['order'])], self.plan['order'])
        self.assertEqual(len(order), 16)
        self.assertEqual(len({t['trial_id'] for t in order}), 16)
        self.assertTrue(all(t['max_calls'] == 1 for t in order))
        self.assertEqual(Counter((s['task_id'], s['feedback_condition']) for s in order),
                         Counter({(t, a): 4 for t in self.plan['task_ids'] for a in prep.ARMS}))
        for slot in order: self.assertEqual(prep.sha(self.output[slot['request_path']]), slot['request_sha256'])
        settings = json.loads(self.output['settings.json']); scope = json.loads(self.output['scope.json'])
        self.assertFalse(scope['execution_authorized'])
        self.assertEqual(scope['proposed_model_requests'], 16)
        self.assertFalse(settings['feedback_after_repair'])
        self.assertFalse(settings['automatic_retries'])
        self.assertFalse(settings['reassign_unused'])
        self.assertEqual(settings['sdk_total_max_attempts_if_executed'], 1)
        self.assertEqual(self.output['source-plan.json'], (prep.STUDY / 'plan.json').read_bytes())
        self.assertEqual(json.loads(self.output['source-plan.json'])['status'], 'prospective_unfrozen')

    def test_diagnostics_transform_is_exact_reversible_single_line_removal(self):
        for task_id, record in self.records.items():
            clean, audit = prep.feedback(record)
            lines = base64.b64decode(record['stdout_base64'], validate=True).splitlines(keepends=True)
            index = audit['removed_line_index_zero_based']
            removed = base64.b64decode(audit['removed_line_base64'], validate=True)
            self.assertEqual(removed, lines[index])
            self.assertIsNotNone(prep.RESULT_LINE.fullmatch(removed))
            self.assertEqual(clean['stdout'].encode(), b''.join(lines[:index] + lines[index + 1:]))
            self.assertEqual(clean['stderr'], record['stderr'])
            self.assertEqual(clean['exit_code'], 4)
            self.assertNotIn('Results File: ', clean['stdout'])
            self.assertIn('a postcondition could not be proved', clean['stdout'])
            self.assertIn('a precondition for this call could not be proved', clean['stdout'])
            for replacement in (b'Results File: /private/unrelated.csv\n', removed + removed):
                bad = copy.deepcopy(record)
                raw = b''.join(lines[:index]) + replacement + b''.join(lines[index + 1:])
                bad.update(stdout=raw.decode(), stdout_base64=base64.b64encode(raw).decode(), stdout_sha256=prep.sha(raw))
                with self.assertRaises(ValueError): prep.feedback(bad)

    def test_no_host_labels_or_analyst_material_leaks(self):
        forbidden = [*self.plan['task_ids'], *self.plan['semantic_instances'], 'dual_fault',
                     'paired_repair', 'caller_only', 'helper_only', 'counterexample', 'reference',
                     'alternative', 'analyst', 'seed', '60865223', '60723362', 'internal-contract-repair-001']
        for payload in self.payloads().values():
            visible = payload['system'][0]['text'] + payload['messages'][0]['content'][0]['text']
            for label in forbidden: self.assertNotIn(label.casefold(), visible.casefold())
        for task in self.tasks:
            parent = self.parents[task['task_id']]
            source = {n: self.output[parent['base_path'] + '/' + n].decode() for n in prep.FILES}
            mutated = copy.deepcopy(task)
            for key in ('task_id', 'semantic_instance', 'counterexamples', 'reference', 'fault_label'):
                mutated[key] = 'HOST_ONLY_SENTINEL_DO_NOT_RENDER'
            original = prep.render(task, source, prep.NOTICE, self.output['syntax.txt'].decode())
            self.assertEqual(original, prep.render(mutated, source, prep.NOTICE, self.output['syntax.txt'].decode()))

    def test_evidence_policy_measurement_and_code_pins_are_complete(self):
        for relative, digest in self.pins.items():
            self.assertEqual(prep.file_sha(prep.safe(prep.REPO, relative)), digest)
        for name, digest in self.gate['pinned_bundles'].items():
            path = str((prep.STUDY / name).relative_to(prep.REPO))
            self.assertEqual(self.pins[path], digest)
        for name in ('prepare.py', 'test_plan.py', 'system.txt', 'syntax.txt'):
            self.assertIn(str((HERE / name).relative_to(prep.REPO)), self.pins)
        self.assertEqual(self.gate['new_verifier_checks'], 2)
        self.assertEqual(self.gate['reused_observations'], 8)
        self.assertFalse(any('authorization.json' in n for n in self.output))

    def test_deterministic_freeze_inventory_rejects_tampering_and_overwrite(self):
        with tempfile.TemporaryDirectory(prefix='.freeze-check-', dir=HERE) as directory:
            first, second = Path(directory) / 'one', Path(directory) / 'two'
            report1, report2 = prep.build(first), prep.build(second)
            self.assertEqual(report1, report2)
            self.assertEqual((first / 'freeze.json').read_bytes(), (second / 'freeze.json').read_bytes())
            with self.assertRaises(ValueError): prep.build(first)
            extra = first / 'unexpected.txt'; extra.write_text('unexpected')
            with self.assertRaises(ValueError): prep.check(first)
            extra.unlink()
            name = next(n for n in self.output if n.startswith('requests/'))
            (first / name).write_bytes((first / name).read_bytes() + b'\n')
            with self.assertRaises(ValueError): prep.check(first)
            # Even updating the local payload hash cannot change the approved rendering.
            manifest = prep.read(first / 'freeze.json'); manifest['files'][name] = prep.file_sha(first / name)
            (first / 'freeze.json').write_bytes(prep.encode(manifest))
            with self.assertRaises(ValueError): prep.check(first)
        actual = HERE / 'frozen-001'
        if actual.exists(): self.assertEqual(prep.check(actual)['payloads'], 4)


if __name__ == '__main__':
    unittest.main(verbosity=2)
