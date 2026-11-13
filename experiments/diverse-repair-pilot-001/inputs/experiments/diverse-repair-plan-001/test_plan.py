"""Offline prospective-plan checks; never imports a model transport or verifier."""
import copy,json,unittest
from unittest.mock import patch
import prepare as p

class Tests(unittest.TestCase):
    def setUp(self):
        self.f=p.HERE/'frozen-001';self.plan=p.load(p.HERE/'plan.json');self.tasks=p.load(p.CURRENT/'tasks.json')
    def test_exact_rebuild_without_network_or_process(self):
        with patch('socket.socket',side_effect=AssertionError('No network')),patch('subprocess.Popen',side_effect=AssertionError('No process')):p.rebuild()
    def test_scope_order_and_budget_fail_closed(self):
        p.validate(self.plan,self.tasks)
        for k,v in [('proposed_calls',25),('max_calls_per_trial',2),('sdk_total_max_attempts',2),('execution_authorized',True),('automatic_retries',True),('reassign_unused',True),('feedback_after_repair',True)]:
            plan=copy.deepcopy(self.plan);plan[k]=v
            with self.assertRaises(AssertionError):p.validate(plan,self.tasks)
        plan=copy.deepcopy(self.plan);plan['order'][0]=plan['order'][1]
        with self.assertRaises(AssertionError):p.validate(plan,self.tasks)
    def test_only_feedback_differs_and_base_is_populated(self):
        guard=p.module(self.f/'policy/body_guard.py')
        for tid,row in p.load(self.f/'parents.json').items():
            task=p.load(self.f/row['task_path']);base=p.files(self.f/row['base_path']);feedback=p.load(self.f/row['feedback_path']);texts={}
            for arm in self.plan['feedback_conditions']:
                req=p.load(self.f/'requests'/(tid+'-'+arm+'.json'));texts[arm]=req['messages'][0]['content'][0]['text']
                expected=p.render(task,base,guard.policy(task),json.dumps(feedback,indent=2) if arm=='verifier_diagnostics' else p.NOTICE)
                self.assertEqual(texts[arm],expected)
                for n,s in base.items():self.assertIn('FILE '+n+'\n```dafny\n'+s,texts[arm])
                self.assertNotIn(task['failure_type'],texts[arm])
                self.assertEqual(req['inferenceConfig'],self.plan['inference_config'])
            self.assertEqual(texts['verifier_diagnostics'].replace(p.OPEN+json.dumps(feedback,indent=2)+p.CLOSE,p.OPEN+p.NOTICE+p.CLOSE),texts['failure_notice_only'])
    def test_diagnostics_exact_except_incidental_csv_line(self):
        for row in p.load(self.f/'parents.json').values():
            original=p.load(self.f/row['original_verifier_path']);clean=p.load(self.f/row['feedback_path'])
            self.assertEqual(clean,p.feedback(original));self.assertEqual(clean['stderr'],original['stderr'])
            self.assertNotIn('Results File:',clean['stdout']);self.assertEqual(clean['exit_code'],4)
            duplicate=dict(original,stdout=original['stdout']+'Results File: /tmp/repodisco-targets-fake/TestResults/f.csv\n')
            with self.assertRaises(AssertionError):p.feedback(duplicate)
    def test_measurement_scope_and_lineage_counts(self):
        gate=p.load(self.f/'validation-gate.json');review=p.load(self.f/'offline-review.json');scope=p.load(self.f/'measurement-scope.json')
        self.assertEqual(gate['planned_controls'],36);self.assertEqual(gate['reused_unchanged_observations'],24)
        self.assertEqual(len(scope['tasks']),6);self.assertEqual(len(scope['control_measurements']),18)
        self.assertEqual(len(review['body_replays']),18);self.assertFalse(review['corrected_proofs_in_model_context'])
        self.assertEqual(len(p.load(self.f/'trials.json')),24)
        self.assertEqual(len(set(t['request_sha256'] for t in p.load(self.f/'trials.json'))),12)
    def test_guard_still_rejects_unsafe_or_unscoped_edits(self):
        guard=p.module(self.f/'policy/body_guard.py');envelope=p.module(self.f/'policy/extract_response.py');adapter=p.module(self.f/'policy/repair_protocol.py')
        for row in p.load(self.f/'parents.json').values():
            task=p.load(self.f/row['task_path']);base=p.files(self.f/row['base_path']);template=p.files(self.f/row['template_path'])
            for body in ('assume false;','reveal K.Cut();','lemma Escape() {}','HelperA.Prove(s,t);'):
                with self.assertRaises(ValueError):adapter.apply_response(json.dumps(dict.fromkeys(task['editable_files'],body)),base,template,task,row['source_sha256'],guard,envelope)

if __name__=='__main__':unittest.main(verbosity=2)
