"""Offline plan, feedback isolation and immutable repair-template checks."""
import copy
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch
import prepare as p
import protocol

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=p.HERE/'frozen-001';cls.plan=p.load(p.HERE/'plan.json')
        cls.parents=p.load(cls.root/'parents.json');cls.trials=p.load(cls.root/'trials.json')
        cls.guard=p.module(cls.root/'policy/body_guard.py');cls.envelope=p.module(cls.root/'policy/extract_response.py')

    def parts(self,tid):
        row=self.parents[tid]
        return row,p.load(self.root/row['task_path']),p.files(self.root/row['base_path']),p.files(self.root/row['template_path'])

    def test_exact_offline_rebuild(self):
        with patch('socket.socket',side_effect=AssertionError('No network')),patch('subprocess.Popen',side_effect=AssertionError('No process')):p.rebuild()

    def test_budget_and_counterbalanced_order_fail_closed(self):
        tasks={tid:self.parts(tid)[1] for tid in self.parents};p.validate(self.plan,tasks)
        for k,v in [('proposed_calls',9),('max_calls_per_trial',2),('automatic_retries',True),('execution_authorized',True),('feedback_after_repair',True),('sdk_total_max_attempts',2),('reassign_unused',True)]:
            plan=copy.deepcopy(self.plan);plan[k]=v
            with self.assertRaises(ValueError):p.validate(plan,tasks)
        plan=copy.deepcopy(self.plan);plan['order'][0]=plan['order'][1]
        with self.assertRaises(ValueError):p.validate(plan,tasks)

    def test_feedback_is_original_except_csv_artifact_line(self):
        for tid,row in self.parents.items():
            raw=p.load(self.root/row['original_verifier_path']);clean=p.load(self.root/row['feedback_path'])
            self.assertEqual(clean,p.feedback(raw))
            lines=raw['stdout'].splitlines(keepends=True);kept=[line for line in lines if not line.startswith('Results File: ')]
            self.assertEqual(''.join(kept),clean['stdout']);self.assertEqual(clean['stderr'],raw['stderr'])
            self.assertEqual(clean['exit_code'],4)
            self.assertIn('a precondition for this call could not be proved',clean['stdout'])
            self.assertNotIn('Results File:',clean['stdout'])
            broken=dict(raw,stdout=raw['stdout']+'Results File: /tmp/repodisco-targets-other/TestResults/a.csv\n')
            with self.assertRaises(ValueError):p.feedback(broken)

    def test_exact_context_and_only_feedback_differs(self):
        for tid in self.parents:
            row,task,base,template=self.parts(tid);texts={}
            for arm in self.plan['feedback_conditions']:
                trial=next(t for t in self.trials if t['parent_trial']==tid and t['feedback_condition']==arm)
                request=p.load(self.root/trial['request_path']);supplied=json.dumps(p.load(self.root/row['feedback_path']),indent=2) if arm=='verifier_diagnostics' else p.NOTICE
                expected=p.prompt(task,base,self.guard.policy(task),supplied)
                self.assertEqual(request['messages'],[dict(role='user',content=[dict(text=expected)])])
                self.assertEqual(request['system'],[dict(text=(p.HERE/'system.txt').read_text())])
                self.assertEqual(request['inferenceConfig'],self.plan['inference_config'])
                for name,source in base.items():self.assertIn('FILE '+name+'\n```dafny\n'+source,expected)
                self.assertNotIn(tid,expected)
                texts[arm]=expected
            detailed=p.OPEN+json.dumps(p.load(self.root/row['feedback_path']),indent=2)+p.CLOSE
            self.assertEqual(texts['verifier_diagnostics'].replace(detailed,p.OPEN+p.NOTICE+p.CLOSE),texts['failure_notice_only'])

    def test_failing_and_verified_repair_bytes_reconstructed(self):
        for tid in self.parents:
            row,task,base,template=self.parts(tid)
            original=p.load(self.root/'parents'/tid/'response.json')['text']
            candidate,_=protocol.apply_response(original,base,template,task,row['source_sha256'],self.guard,self.envelope)
            self.assertEqual(candidate,base)
            repaired=p.files(p.DIAG/'fixtures'/(tid+'-reordered'));bodies={}
            for name in task['editable_files']:
                pre,suf=self.guard.split_seed(template[name]);bodies[name]=repaired[name][len(pre):-len(suf)]
            candidate,_=protocol.apply_response(json.dumps(bodies),base,template,task,row['source_sha256'],self.guard,self.envelope)
            self.assertEqual(candidate,repaired)
            for trial in [t for t in self.trials if t['parent_trial']==tid]:
                text=p.load(self.root/trial['request_path'])['messages'][0]['content'][0]['text']
                self.assertTrue(all(body not in text for body in bodies.values()))

    def test_stale_or_contract_changed_bases_rejected(self):
        tid=next(iter(self.parents));row,task,base,template=self.parts(tid)
        raw=p.load(self.root/'parents'/tid/'response.json')['text']
        changed=dict(base);changed['HelperA.dfy']=changed['HelperA.dfy'].replace('requires forall','requires false\n    requires forall')
        with self.assertRaises(ValueError):protocol.apply_response(raw,changed,template,task,row['source_sha256'],self.guard,self.envelope)
        with self.assertRaises(ValueError):protocol.apply_response(raw,changed,template,task,protocol.hashes(changed),self.guard,self.envelope)
        changed=dict(base);changed['Kernel.dfy']+='\n'
        with self.assertRaises(ValueError):protocol.apply_response(raw,changed,template,task,protocol.hashes(changed),self.guard,self.envelope)
        for body in ['assume false;','lemma Prove() ensures true {}']:
            with self.assertRaises(ValueError):protocol.apply_response(json.dumps(dict.fromkeys(task['editable_files'],body)),base,template,task,row['source_sha256'],self.guard,self.envelope)

    def test_eight_fresh_slots_but_four_payloads_and_two_workspaces(self):
        self.assertEqual(len(self.trials),8);self.assertEqual(len({t['trial_id'] for t in self.trials}),8)
        self.assertEqual(len({t['request_sha256'] for t in self.trials}),4)
        self.assertEqual(len({tuple(sorted(row['source_sha256'].items())) for row in self.parents.values()}),2)
        for trial in self.trials:
            self.assertEqual(p.sha(self.root/trial['request_path']),trial['request_sha256']);self.assertEqual(trial['max_calls'],1)
            self.assertTrue(trial['trial_id'].startswith('map-repair-'))
        scope=p.load(self.root/'target-scope.json');self.assertFalse(scope['supplied_clients_are_model_credit'])
        for row in scope['tasks'].values():self.assertEqual(len(row['editable_targets']),1 if len(row['target_dependencies']['HelperB.Prove']) else 2)

    def test_existing_freeze_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileExistsError):p.build(Path(tmp))

if __name__=='__main__':unittest.main(verbosity=2)
