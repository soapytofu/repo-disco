"""Offline plan and exact saved-evidence checks; no model or verifier dispatch."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import prepare as p


class PlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan=p.load(p.HERE/'plan.json')
        with patch('socket.socket',side_effect=AssertionError('No network')),patch('subprocess.Popen',side_effect=AssertionError('No process')):
            cls.groups=p.reviewed_groups(cls.plan)
            cls.protocol,_=p.checked_protocol(cls.plan)
            cls.guard=p.module(cls.protocol/'body_guard.py')
            cls.envelope=p.module(cls.protocol/'extract_response.py')
            cls.adapter=p.module(cls.protocol/'repair_protocol.py')

    def test_balanced_scope_and_aggregate_budget(self):
        p.validate_plan(self.plan)
        for key,value in [('proposed_calls',33),('max_calls_per_trial',2),('sdk_total_max_attempts',2),
                          ('execution_authorized',True),('automatic_retries',True),('reassign_unused',True),
                          ('feedback_after_repair',True),('max_output_tokens_total',4096)]:
            plan=copy.deepcopy(self.plan);plan[key]=value
            with self.assertRaises(AssertionError):p.validate_plan(plan)
        plan=copy.deepcopy(self.plan);plan['order'][0]=plan['order'][1]
        with self.assertRaises(AssertionError):p.validate_plan(plan)
        self.assertEqual(sum(x['review']['planned'] for x in self.groups.values()),78)
        self.assertEqual(len(self.plan['order']),32)

    def test_original_diagnostic_fidelity_and_refusal_to_strip_other_content(self):
        for group in self.groups.values():
            for task in group['tasks']:
                record=group['records'][task['task_id']+'-faulty'];clean=p.feedback(record)
                self.assertEqual(clean['stderr'],record['stderr'])
                self.assertEqual(clean['exit_code'],4)
                originals=record['stdout'].splitlines(keepends=True)
                self.assertEqual(clean['stdout'],''.join(s for s in originals if not s.startswith('Results File: ')))
                altered=dict(record,stdout=record['stdout']+'Results File: /tmp/repodisco-repair-fake/TestResults/x.csv\n')
                with self.assertRaises(AssertionError):p.feedback(altered)
                altered=dict(record,stdout=record['stdout'].replace('/tmp/repodisco-repair','/unapproved/location'))
                with self.assertRaises(AssertionError):p.feedback(altered)

    def test_only_feedback_differs_without_positive_or_metadata_hints(self):
        for group in self.groups.values():
            for task in group['tasks']:
                tid=task['task_id'];base=p.files(group['root']/group['case_by_id'][tid+'-faulty']['path'])
                clean=p.feedback(group['records'][tid+'-faulty'])
                detailed=p.render(task,base,self.guard.policy(task),json.dumps(clean,indent=2))
                control=p.render(task,base,self.guard.policy(task),p.NOTICE)
                self.assertEqual(detailed.replace(p.OPEN+json.dumps(clean,indent=2)+p.CLOSE,p.OPEN+p.NOTICE+p.CLOSE),control)
                for name,source in base.items():self.assertIn('FILE '+name+'\n```dafny\n'+source,detailed)
                if task.get('failure_type'):self.assertNotIn(task['failure_type'],detailed)
                self.assertNotIn('Counterexample:',detailed)
                self.assertNotIn('Correct repair:',detailed)
                self.assertNotIn('feasibility_derivation',detailed)
                template=p.files(group['root']/group['case_by_id'][tid+'-empty']['path'])
                for variant in ('reference','alternative'):
                    src=p.files(group['root']/group['case_by_id'][tid+'-'+variant]['path'])
                    for name in task['editable_files']:
                        prefix,suffix=self.guard.split_seed(template[name]);body=src[name][len(prefix):-len(suffix)]
                        self.assertNotIn(body,detailed)
                        self.assertNotIn(body,control)

    def test_prospective_protocol_replays_exact_constructed_states(self):
        count=0
        for group in self.groups.values():
            for task in group['tasks']:
                tid=task['task_id'];base=p.files(group['root']/group['case_by_id'][tid+'-faulty']['path'])
                template=p.files(group['root']/group['case_by_id'][tid+'-empty']['path'])
                for variant in ('faulty','reference','alternative'):
                    source=p.files(group['root']/group['case_by_id'][tid+'-'+variant]['path']);payload={}
                    for name in task['editable_files']:
                        prefix,suffix=self.guard.split_seed(template[name]);payload[name]=source[name][len(prefix):-len(suffix)]
                    rebuilt,_=self.adapter.apply_response(json.dumps(payload),base,template,task,p.hashes(base),self.guard,self.envelope)
                    self.assertEqual(rebuilt,source);count+=1
        self.assertEqual(count,24)

    def test_named_measurements_keep_provider_and_client_dependencies(self):
        with patch('socket.socket',side_effect=AssertionError('No network')),patch('subprocess.Popen',side_effect=AssertionError('No process')):
            measured=p.assemble_measurements(self.plan,self.groups)
        self.assertEqual(measured,p.load(p.HERE/'measurement-scope.json'))
        self.assertEqual(len(measured['tasks']),8)
        self.assertEqual(len(measured['control_measurements']),24)
        for row in measured['control_measurements']:
            self.assertTrue(row['supplied_providers_verified'])
            if row['case_id'].endswith('-faulty'):
                self.assertEqual(row['editable_local']['passed'],0)
                self.assertEqual(row['supplied_clients_closed']['passed'],0)
                self.assertEqual(row['supplied_clients_local']['passed'],2)
        for tid,scope in measured['tasks'].items():
            self.assertLess(p.METRIC_TARGETS,set(scope['expected_units']))
            self.assertEqual(scope['target_dependencies']['HelperB.Prove'],['HelperA.Prove'] if tid.endswith('-shared') else [])

    def test_guard_rejects_escape_and_protected_parent_changes(self):
        for group in self.groups.values():
            for task in group['tasks']:
                tid=task['task_id'];base=p.files(group['root']/group['case_by_id'][tid+'-faulty']['path'])
                template=p.files(group['root']/group['case_by_id'][tid+'-empty']['path'])
                for body in ('assume false;','reveal K.Feasible();','lemma Escape() {}','HelperA.Prove(s);'):
                    with self.assertRaises(ValueError):
                        self.adapter.apply_response(json.dumps(dict.fromkeys(task['editable_files'],body)),base,template,task,p.hashes(base),self.guard,self.envelope)
                changed=dict(base);changed['ClientA.dfy']+='\n'
                with self.assertRaises(ValueError):
                    self.adapter.apply_response(json.dumps(dict.fromkeys(task['editable_files'],'')),changed,template,task,p.hashes(base),self.guard,self.envelope)

    def test_invalid_coordinator_gate_blocks_before_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'blocked-freeze'
            with patch.object(p,'validated_freeze_gate',side_effect=AssertionError('Coordinator review missing')):
                with self.assertRaises(AssertionError):p.build(out)
            self.assertFalse(out.exists())

    def test_exact_frozen_rebuild_without_processes(self):
        if not (p.HERE/'frozen-001').exists(): self.skipTest('Exact freeze not created yet')
        with patch('socket.socket',side_effect=AssertionError('No network')),patch('subprocess.Popen',side_effect=AssertionError('No process')):
            p.rebuild()

    def test_standalone_frozen_guard_and_registry(self):
        frozen=p.HERE/'frozen-001'
        if not frozen.exists(): self.skipTest('Exact freeze not created yet')
        guard=p.module(frozen/'policy/body_guard.py')
        envelope=p.module(frozen/'policy/extract_response.py')
        adapter=p.module(frozen/'policy/repair_protocol.py')
        self.assertEqual(guard.ROOT,frozen/'policy')
        self.assertEqual(adapter.ROOT,frozen/'policy')
        count=0
        with patch('socket.socket',side_effect=AssertionError('No network')),patch('subprocess.Popen',side_effect=AssertionError('No process')):
            for tid,parent in p.load(frozen/'parents.json').items():
                task=p.load(frozen/parent['task_path']);base=p.files(frozen/parent['base_path']);template=p.files(frozen/parent['template_path'])
                payload={}
                for name in task['editable_files']:
                    prefix,suffix=guard.split_seed(template[name]);payload[name]=base[name][len(prefix):-len(suffix)]
                rebuilt,_=adapter.apply_response(json.dumps(payload),base,template,task,parent['source_sha256'],guard,envelope)
                self.assertEqual(rebuilt,base);count+=1
                with self.assertRaises(ValueError):
                    adapter.apply_response(json.dumps(dict.fromkeys(task['editable_files'],'assume false;')),base,template,task,parent['source_sha256'],guard,envelope)
        self.assertEqual(count,8)


if __name__=='__main__':
    unittest.main(verbosity=2)
