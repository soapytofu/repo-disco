"""Proposal gates and exact payload tests with network/process dispatch disabled."""
import copy,json,tempfile,unittest
from collections import Counter
from pathlib import Path
from unittest.mock import patch
import prepare as p

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan=p.load(p.HERE/'plan.json');cls.tasks=p.load(p.REV/'tasks.json')
    def test_balanced_order_and_no_authorization(self):
        p.validate_plan(self.plan,self.tasks)
        self.assertFalse(self.plan['execution_authorized'])
    def test_budget_order_and_retry_mutations_rejected(self):
        for key,value in [('proposed_calls',33),('execution_authorized',True),('sdk_total_max_attempts',2),('feedback',True),('reassign_unused',True),('automatic_retries',True)]:
            bad=copy.deepcopy(self.plan);bad[key]=value
            with self.assertRaises(ValueError):p.validate_plan(bad,self.tasks)
        bad=copy.deepcopy(self.plan);bad['replicates'][0][0][0]=bad['replicates'][0][0][1]
        with self.assertRaises(ValueError):p.validate_plan(bad,self.tasks)
    def test_frozen_hashes_and_exact_offline_rebuild(self):
        with patch('socket.socket',side_effect=AssertionError('Network prohibited')),patch('subprocess.Popen',side_effect=AssertionError('Process dispatch prohibited')):
            p.validate()
    def test_every_prompt_contains_only_its_exact_seed_context(self):
        out=p.HERE/'frozen-001';guard=p.common['guard'](out/'policy/body_guard.py')
        for t in self.tasks:
            seeds=p.common['files'](out/'seeds'/t['task_id'])
            self.assertEqual(p.inventory(out/'seeds'/t['task_id']),t['source_sha256'])
            request=p.load(out/'requests'/(t['task_id']+'.json'))
            self.assertEqual(request['messages'],[dict(role='user',content=[dict(text=p.prompt(t,seeds,guard.policy(t)))])])
            self.assertEqual(len(request['system']),1)
            self.assertEqual(request['inferenceConfig'],self.plan['inference_config'])
    def test_repeats_share_payload_not_conversation(self):
        out=p.HERE/'frozen-001';trials=p.load(out/'trials.json')
        self.assertEqual(len(trials),32);self.assertEqual(len({t['trial_id'] for t in trials}),32)
        byid={}
        for t in trials:
            self.assertEqual(p.sha(out/t['request_path']),t['request_sha256'])
            byid.setdefault(t['task_id'],[]).append(t)
        for pair in byid.values():
            self.assertEqual(len(pair),2);self.assertEqual({t['sample'] for t in pair},{1,2})
            self.assertEqual(pair[0]['request_sha256'],pair[1]['request_sha256'])
        self.assertEqual(self.plan['max_output_tokens_total'],131072)
    def test_prompt_syntax_examples_admitted_for_every_task(self):
        guard=p.common['guard'](p.HERE/'frozen-001/policy/body_guard.py')
        examples=['assert true;','var tmp := 0;','if true { assert true; } else { assert true; }','forall k0 | k0 == 0 ensures k0 == 0 { assert k0 == 0; }']
        for t in self.tasks:
            for text in examples:
                g=guard.Grammar(text,t);g.sequence();self.assertIsNone(g.peek())
    def test_refuses_overwriting_existing_bundle(self):
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp)/'exists';out.mkdir()
            with self.assertRaises(FileExistsError):p.build(out)

if __name__=='__main__':unittest.main(verbosity=2)
