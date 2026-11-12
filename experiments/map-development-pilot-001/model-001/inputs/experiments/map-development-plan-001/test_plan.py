import copy
import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import prepare as p


class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan=p.load(p.HERE/'plan.json');cls.tasks=p.load(p.HERE/'frozen-001/tasks.json')
    def test_exact_offline_rebuild(self):
        with patch('socket.socket',side_effect=AssertionError('No network')),patch('subprocess.Popen',side_effect=AssertionError('No processes')):p.rebuild()
    def test_budget_and_order_fail_closed(self):
        p.validate(self.plan,self.tasks)
        for k,v in [('proposed_calls',17),('execution_authorized',True),('sdk_total_max_attempts',2),('feedback',True),('reassign_unused',True)]:
            plan=copy.deepcopy(self.plan);plan[k]=v
            with self.assertRaises(ValueError):p.validate(plan,self.tasks)
        plan=copy.deepcopy(self.plan);plan['replicates'][0][0]=plan['replicates'][0][1]
        with self.assertRaises(ValueError):p.validate(plan,self.tasks)
    def test_exact_seed_context_and_only_declared_bindings(self):
        root=p.HERE/'frozen-001';bindings=p.load(root/'policy-bindings.json')
        for task in self.tasks:
            seed=p.files(root/'seeds'/task['task_id']);guard=p.module(root/bindings[task['task_id']]['body_guard'])
            request=p.load(root/'requests'/(task['task_id']+'.json'))
            self.assertEqual(request['messages'],[dict(role='user',content=[dict(text=p.prompt(task,seed,guard.policy(task)))])])
            self.assertEqual(request['inferenceConfig'],self.plan['inference_config'])
            self.assertEqual(p.inventory(root/'seeds'/task['task_id']),task['source_sha256'])
    def test_syntax_examples_admitted_without_rewrites(self):
        root=p.HERE/'frozen-001';bindings=p.load(root/'policy-bindings.json')
        examples=[s for s in re.findall(r'`([^`]+)`',(p.HERE/'syntax.txt').read_text()) if s.endswith(';') or s.endswith('}')]
        self.assertEqual(len(examples),5)
        for task in self.tasks:
            guard=p.module(root/bindings[task['task_id']]['body_guard'])
            for body in examples:
                parser=guard.Grammar(body,task);parser.sequence();self.assertIsNone(parser.peek())
    def test_two_fresh_slots_per_workspace(self):
        root=p.HERE/'frozen-001';trials=p.load(root/'trials.json');self.assertEqual(len(trials),16)
        self.assertEqual(len({r['trial_id'] for r in trials}),16)
        for task in self.tasks:
            pair=[r for r in trials if r['task_id']==task['task_id']]
            self.assertEqual({r['sample'] for r in pair},{1,2})
            self.assertEqual(pair[0]['request_sha256'],pair[1]['request_sha256'])
            self.assertEqual(p.sha(root/pair[0]['request_path']),pair[0]['request_sha256'])
    def test_existing_freeze_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(FileExistsError):p.build(Path(temp))
    def test_target_scope_separates_supplied_and_editable_work(self):
        scope=p.load(p.HERE/'frozen-001/target-scope.json')
        self.assertFalse(scope['supplied_clients_are_model_credit'])
        self.assertFalse(scope['provider_obligations_are_model_credit'])
        self.assertEqual(set(scope['tasks']),{t['task_id'] for t in self.tasks})
        for task in self.tasks:
            row=scope['tasks'][task['task_id']]
            self.assertEqual(row['editable_targets'],[n.removesuffix('.dfy')+'.Prove' for n in task['editable_files']])
            self.assertEqual(row['target_dependencies']['HelperB.Prove'],['HelperA.Prove'] if task['sharing']=='shared' else [])
            self.assertEqual(sum(len(x) for x in row['expected_units'].values()),14 if task['semantic_instance']=='fresh_move' else 20)


if __name__=='__main__':unittest.main(verbosity=2)
