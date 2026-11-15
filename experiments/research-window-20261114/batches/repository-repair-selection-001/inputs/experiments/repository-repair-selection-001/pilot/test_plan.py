"""Offline design/gate tests; actual prompt tests wait for root endorsement."""
import copy
import csv
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import prepare as p


def synthetic_csv(interpreter, failed=()):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(interpreter.HEADER)
    for symbol in sorted(p.TARGETS|{'Provider.Certify'}):
        writer.writerow([symbol+' (correctness)','Failed' if symbol in failed else 'Passed','0.01','1','0'])
    return {'synthetic.csv':output.getvalue()}


class PlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = p.load(p.HERE/'plan.json')

    def require_review(self):
        gate = p.HERE/'freeze-gate.json'
        if not gate.exists() or not p.load(gate).get('coordinator_reviewed',False):
            self.skipTest('Root has not endorsed actual source/protocol/measurement bindings')

    def test_original_order_balance_and_single_aggregate_allocation(self):
        p.validate_plan(self.plan)
        for key,value in [('proposed_calls',33),('max_calls_per_trial',2),('sdk_total_max_attempts',2),
                          ('replicates_per_cell',2),('unique_failing_workspaces',8),('unique_payloads',16),
                          ('execution_authorized',True),('automatic_retries',True),('reassign_unused',True),
                          ('feedback_after_repair',True),('max_output_tokens_total',4096)]:
            altered = copy.deepcopy(self.plan)
            altered[key] = value
            with self.assertRaises(AssertionError): p.validate_plan(altered)
        altered = copy.deepcopy(self.plan)
        altered['order_slots'][0],altered['order_slots'][1] = altered['order_slots'][1],altered['order_slots'][0]
        with self.assertRaises(AssertionError): p.validate_plan(altered)

    def test_exact_task_ids_and_separate_typed_environments(self):
        tasks = p.task_metadata(self.plan)
        self.assertEqual(len(tasks),4)
        guard = p.module(p.safe(p.REPO,self.plan['protocol_root'])/'body_guard.py')
        for task in tasks.values():
            entry = guard.task_entry(task)
            self.assertEqual(entry['semantic_instance'],task['semantic_instance'])
            rules = entry['file_rules']
            self.assertNotIn('H.Prove',rules['HelperA.dfy']['calls'])
            self.assertIn('H.Prove',rules['HelperB.dfy']['calls'])
            self.assertEqual(rules['HelperB.dfy']['call_types']['H.Prove'],
                             [rules['HelperA.dfy']['parameter_types'][n] for n in rules['HelperA.dfy']['variables']])
        self.assertEqual(tasks['inverse_exchange_pipeline']['semantic_instance'],'inverse_exchange_pipeline')
        altered = dict(tasks['inverse_exchange_pipeline'],semantic_instance='inverse_exchange')
        with self.assertRaises(ValueError): guard.task_entry(altered)

    def test_synthetic_feedback_removes_only_one_incidental_path_line(self):
        record = dict(exit_code=4,attempts=1,model_calls=0,
                      stdout='SYNTHETIC HelperA.dfy(1,1): Error: example\r\nResults File: /tmp/repodisco-repair-adapter-example/TestResults/example.csv\r\nDafny program verifier finished with 3 verified, 1 error\r\n',
                      stderr='SYNTHETIC stderr exactly retained\n')
        cleaned = p.feedback(record)
        self.assertEqual(cleaned['stderr'],record['stderr'])
        self.assertEqual(cleaned['stdout'],record['stdout'].replace('Results File: /tmp/repodisco-repair-adapter-example/TestResults/example.csv\r\n',''))
        with self.assertRaises(AssertionError):
            p.feedback(dict(record,stdout=record['stdout']+'Results File: /tmp/repodisco-repair-other/TestResults/second.csv\n'))
        with self.assertRaises(AssertionError):
            p.feedback(dict(record,stdout=record['stdout'].replace('/tmp/repodisco-repair-adapter-example','/unapproved/location')))

    def test_synthetic_render_uses_only_source_rules_and_feedback(self):
        task = dict(editable_files=p.EDITABLE,faulty_file='SECRET_FAULT',primary_case_id='SECRET_CASE',
                    expected_targets='SECRET_EXPECTATION',reference='SECRET_REFERENCE',counterexample='SECRET_COUNTEREXAMPLE')
        rules = {name:dict(variables=['x'],parameter_types={'x':'int'},calls={'O.Use':1},call_types={'O.Use':['int']},
                          pure={'K.Valid':1},pure_types={'K.Valid':dict(arguments=['int'],result='bool')}) for name in p.EDITABLE}
        source = {'HelperA.dfy':'module SyntheticA {}\n','HelperB.dfy':'include "HelperA.dfy"\nmodule SyntheticB {}\n'}
        detailed = p.render(task,source,rules,'SYNTHETIC_DIAGNOSTIC')
        notice = p.render(task,source,rules,p.NOTICE)
        self.assertEqual(detailed.replace(p.OPEN+'SYNTHETIC_DIAGNOSTIC'+p.CLOSE,p.OPEN+p.NOTICE+p.CLOSE),notice)
        for value in task.values():
            if isinstance(value,str): self.assertNotIn(value,detailed)
        for name,text in source.items(): self.assertIn('FILE '+name+'\n```dafny\n'+text+'```',detailed)
        self.assertIn('Body environment for HelperA.dfy',detailed)
        self.assertIn('Body environment for HelperB.dfy',detailed)

    def test_synthetic_named_scope_separates_local_and_closed_clients(self):
        metrics = p.module(p.safe(p.REPO,self.plan['measurement_interpreter']))
        for failing in ('HelperA.Prove','HelperB.Prove'):
            records = {f'fake-{v}':{'csv':synthetic_csv(metrics,([failing] if v=='faulty' else []))}
                       for v in ('reference','alternative','faulty')}
            scope,rows = p.measure_task({'task_id':'fake'},records,metrics)
            self.assertEqual(scope['target_dependencies'],p.GRAPH)
            self.assertLess(p.TARGETS,set(scope['expected_units']))
            row = rows[-1]
            self.assertEqual(row['editable_local'],dict(passed=1,total=2))
            self.assertEqual(row['supplied_clients_local'],dict(passed=2,total=2))
            self.assertEqual(row['supplied_clients_closed'],dict(passed=0,total=2))
            self.assertTrue(row['supplied_providers_verified'])
            altered = copy.deepcopy(records)
            altered['fake-faulty']['csv'] = synthetic_csv(metrics,[failing,'Provider.Certify'])
            with self.assertRaises(AssertionError): p.measure_task({'task_id':'fake'},altered,metrics)
            altered['fake-faulty']['csv'] = synthetic_csv(metrics,['HelperA.Prove','HelperB.Prove'])
            with self.assertRaises(AssertionError): p.measure_task({'task_id':'fake'},altered,metrics)

    def test_missing_or_rejected_gate_precedes_output_and_rendering(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)/'not-created'
            with patch.object(p,'reviewed_groups',return_value={}), \
                 patch.object(p,'checked_protocol',return_value=(Path(tmp),{})), \
                 patch.object(p,'validated_freeze_gate',side_effect=AssertionError('No coordinator endorsement')), \
                 patch.object(p,'render',side_effect=AssertionError('Must not render')) as render:
                with self.assertRaisesRegex(AssertionError,'coordinator'): p.build(out)
                render.assert_not_called()
            self.assertFalse(out.exists())
            with patch.object(p,'reviewed_groups',side_effect=FileNotFoundError('Missing reviewed sources')), \
                 patch.object(p,'checked_protocol') as protocol:
                with self.assertRaises(FileNotFoundError): p.build(out)
                protocol.assert_not_called()
            self.assertFalse(out.exists())

    def test_prospective_status_has_no_model_or_frozen_artifacts(self):
        current = p.status()
        self.assertEqual(current['proposed_calls'],32)
        self.assertEqual(current['model_calls'],0)
        if not (p.HERE/'freeze-gate.json').exists():
            self.assertFalse(current['coordinator_ready'])
            self.assertFalse(current['frozen_exists'])
            self.assertFalse((p.HERE/'requests').exists())

    def test_transitive_review_inventory_includes_and_validates_every_pin(self):
        actual = p.reviewed_auditor_inputs(self.plan)
        root = p.safe(p.REPO,self.plan['source_review_code']).parent
        pins = p.load(root/'review-manifest.json')
        self.assertEqual(actual,{root/'review-manifest.json',*(root/name for name in pins)})
        self.assertIn(root/'review-inputs/review_verification.py',actual)
        self.assertIn(root/'test_review_verification.py',actual)
        self.assertIn(root/'review-tests.log',actual)
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            study = repo/'study'
            study.mkdir()
            contents = {'review_verification.py':'# synthetic entry\n', 'review-scope.json':'{}\n',
                        'review-inputs/review_verification.py':'# synthetic transitive auditor\n',
                        'review-inputs/README.md':'synthetic nested file\n',
                        'test_review_verification.py':'# synthetic test\n','review-tests.log':'synthetic log\n'}
            for name,text in contents.items():
                target = study/name
                target.parent.mkdir(parents=True,exist_ok=True)
                target.write_text(text)
            snapshot = {name:p.sha(study/name) for name in contents}
            p.save(study/'review-manifest.json',snapshot)
            plan = dict(source_review_code='study/review_verification.py',source_review_scope='study/review-scope.json')
            with patch.object(p,'REPO',repo):
                self.assertEqual(p.reviewed_auditor_inputs(plan),{study/'review-manifest.json',*(study/name for name in contents)})
                nested = study/'review-inputs/review_verification.py'
                nested.write_text('changed\n')
                with self.assertRaisesRegex(AssertionError,'dependency changed'): p.reviewed_auditor_inputs(plan)
                nested.unlink()
                with self.assertRaises(FileNotFoundError): p.reviewed_auditor_inputs(plan)
                p.save(study/'review-manifest.json',{k:v for k,v in snapshot.items() if k!='review-inputs/review_verification.py'})
                with self.assertRaisesRegex(AssertionError,'Incomplete study-review'): p.reviewed_auditor_inputs(plan)

    def test_reviewed_measurements_and_feedback_pairs_when_endorsed(self):
        self.require_review()
        with patch('socket.socket',side_effect=AssertionError('No network')),patch('subprocess.Popen',side_effect=AssertionError('No process')):
            groups = p.reviewed_groups(self.plan)
            root,_ = p.checked_protocol(self.plan)
            p.validated_freeze_gate(self.plan,groups)
            measured = p.assemble_measurements(self.plan,groups)
            self.assertEqual(measured,p.load(p.HERE/'measurement-scope.json'))
            self.assertEqual((len(measured['tasks']),len(measured['control_measurements'])),(4,12))
            guard = p.module(root/'body_guard.py')
            for group in groups.values():
                for task in group['tasks']:
                    tid = task['task_id']
                    base = p.files(group['root']/group['case_by_id'][tid+'-faulty']['path'])
                    clean = p.feedback(group['records'][tid+'-faulty'])
                    detailed = p.render(task,base,guard.task_entry(task)['file_rules'],json.dumps(clean,indent=2))
                    notice = p.render(task,base,guard.task_entry(task)['file_rules'],p.NOTICE)
                    self.assertEqual(detailed.replace(p.OPEN+json.dumps(clean,indent=2)+p.CLOSE,p.OPEN+p.NOTICE+p.CLOSE),notice)
                    for name,text in base.items(): self.assertIn('FILE '+name+'\n```dafny\n'+text+'```',detailed)
                    self.assertNotIn('seeded_fault_module',detailed)
                    self.assertNotIn('primary_case_id',detailed)
                    self.assertNotIn('expected_local_targets',detailed)

    def test_exact_frozen_rebuild_when_endorsed(self):
        self.require_review()
        if not (p.HERE/'frozen-001').exists(): self.skipTest('Prompt freeze not built')
        with patch('socket.socket',side_effect=AssertionError('No network')),patch('subprocess.Popen',side_effect=AssertionError('No process')):
            p.rebuild()

    def test_standalone_frozen_protocol_when_endorsed(self):
        self.require_review()
        frozen = p.HERE/'frozen-001'
        if not frozen.exists(): self.skipTest('Prompt freeze not built')
        guard,envelope,adapter = (p.module(frozen/'policy'/name) for name in ('body_guard.py','extract_response.py','repair_protocol.py'))
        self.assertEqual(guard.POLICY_ID,p.POLICY_ID)
        self.assertEqual(guard.ROOT,frozen/'policy')
        parents = p.load(frozen/'parents.json')
        self.assertEqual(len(parents),4)
        for tid,parent in parents.items():
            task = p.load(frozen/parent['task_path'])
            base,template = p.files(frozen/parent['base_path']),p.files(frozen/parent['template_path'])
            bodies = {}
            for name in p.EDITABLE:
                prefix,suffix = guard.split_seed(template[name])
                bodies[name] = base[name][len(prefix):-len(suffix)]
            rebuilt,_ = adapter.apply_response(json.dumps(bodies),base,template,task,parent['source_sha256'],guard,envelope)
            self.assertEqual(rebuilt,base)
            with self.assertRaises(ValueError):
                adapter.apply_response(json.dumps(dict.fromkeys(p.EDITABLE,'assume false;')),base,template,task,parent['source_sha256'],guard,envelope)


if __name__=='__main__':
    unittest.main(verbosity=2)
