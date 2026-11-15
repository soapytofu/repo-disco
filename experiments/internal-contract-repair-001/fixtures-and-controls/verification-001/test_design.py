"""Offline construction, provenance and semantic checks; no verifier or API."""
from pathlib import Path
import base64
import itertools
import json
import tempfile
import unittest
import build as b

ROOT=Path(__file__).resolve().parent
def read(name):return json.loads((ROOT/name).read_bytes())
def source(path):return {p.name:p.read_bytes() for p in sorted((ROOT/path).glob('*.dfy'))}
def endpoint(start,length,cap):return min(start+length,cap)
def advance(start,length,cap):return min(length,cap-start)
def erase(m,key):return {x:y for x,y in m.items() if x!=key}
def entry(m,key):return {x:y for x,y in m.items() if x==key}


class Construction(unittest.TestCase):
    def test_rebuild_and_only_two_genuinely_new_workspaces(self):
        cases=read('cases.json');tasks=read('tasks.json')
        self.assertEqual(len(cases),2);self.assertEqual(len(tasks),2)
        self.assertEqual(len(read('reused-controls.json')),8)
        oldcases=read('inputs/parent/cases.json')
        oldinventories={tuple(sorted(c['source_sha256'].items())) for c in oldcases}
        for case in cases:
            self.assertNotIn(tuple(sorted(case['source_sha256'].items())),oldinventories)
            self.assertEqual(case['expected_local_targets'],{'Helper.Transfer':False,'Client.Target':False})
            self.assertEqual(case['expected_target_diagnostics'],{'Helper.Transfer':['postcondition'],'Client.Target':['precondition']})
            self.assertTrue(case['new_verifier_observation'])
        with tempfile.TemporaryDirectory() as directory:
            other=Path(directory);result=b.generate(other,ROOT)
            self.assertEqual(result,{'fresh_checks':2,'reused_controls':8,'source_files':8,'model_calls':0})
            for name in ('tasks.json','cases.json','reused-controls.json','lineage.json','parent-inputs.json','fixture-manifest.json'):
                self.assertEqual((ROOT/name).read_bytes(),(other/name).read_bytes(),name)
            for name,digest in read('fixture-manifest.json').items():
                self.assertEqual(b.sha((other/name).read_bytes()),digest,name)

    def test_exact_new_headers_old_bodies_and_public_kernel_protection(self):
        oldtasks={t['task_id']:t for t in read('inputs/parent/tasks.json')}
        for task in read('tasks.json'):
            old_id=task['parent_task_id'];old=source('inputs/parent/fixtures/'+old_id+'/reference')
            fixed=source(task['path']);new=source('inputs/parent/fixtures/'+old_id+'/contract_only')
            self.assertEqual(fixed['Helper.dfy'],new['Helper.dfy'])
            self.assertEqual(fixed['Client.dfy'],old['Client.dfy'])
            self.assertEqual(b.body(fixed['Helper.dfy']),b.body(old['Helper.dfy']))
            self.assertEqual(b.body(fixed['Client.dfy']),b.body(old['Client.dfy']))
            self.assertEqual(task['template_sha256'],task['source_sha256'])
            self.assertEqual(task['template_path'],task['path'])
            self.assertEqual(task['fixed_helper_prefix'],oldtasks[old_id]['internal_api_versions']['new']['header']+'  {\n')
            for name in ('Kernel.dfy','All.dfy'):self.assertEqual(fixed[name],old[name])
            b.assert_scope(task,fixed)
            tampered=dict(fixed);tampered['Client.dfy']=fixed['Client.dfy'].replace(b'    ensures ',b'    ensures true || ',1)
            with self.assertRaisesRegex(AssertionError,'Protected method header'):b.assert_scope(task,tampered)
            tampered=dict(fixed);tampered['Helper.dfy']=old['Helper.dfy']
            with self.assertRaisesRegex(AssertionError,'Protected method header'):b.assert_scope(task,tampered)
            tampered=dict(fixed);tampered['Kernel.dfy']+=b'\n'
            with self.assertRaisesRegex(AssertionError,'Protected file'):b.assert_scope(task,tampered)

    def test_eight_controls_are_exact_one_or_two_body_repairs_with_old_evidence(self):
        tasks={t['task_id']:t for t in read('tasks.json')}
        inventory=b.validate_inputs(ROOT)
        report=read('inputs/parent/'+b.REVIEW)
        checks={c['case_id']:c for c in report['checks']}
        self.assertEqual(inventory['parent_job_id'],'60723362')
        for control in read('reused-controls.json'):
            task=tasks[control['task_id']];files=source(control['path']);seed=source(task['path'])
            self.assertEqual(b.hashes(files),control['source_sha256'])
            b.assert_scope(task,files)
            changed=[name for name in b.EDITABLE if files[name]!=seed[name]]
            self.assertEqual(changed,control['changed_editable_files'])
            record=read(control['evidence_path']);old=checks[control['parent_case_id']]
            self.assertEqual(record['source_sha256'],control['source_sha256'])
            self.assertEqual(b.sha((ROOT/control['evidence_path']).read_bytes()),old['evidence_sha256'])
            self.assertTrue(control['reused_evidence']);self.assertFalse(control['new_verifier_observation'])
            self.assertEqual(control['observed_local_targets'],old['named_evidence']['local_targets'])
            for stream in ('stdout','stderr'):
                raw=base64.b64decode(record[stream+'_base64'],validate=True)
                self.assertEqual(b.sha(raw),record[stream+'_sha256'])
            if control['role']=='helper_body_only_repair':
                self.assertEqual(changed,['Helper.dfy'])
                self.assertEqual(control['observed_local_targets'],{'Helper.Transfer':True,'Client.Target':False})
            elif control['role']=='client_body_only_repair':
                self.assertEqual(changed,['Client.dfy'])
                self.assertEqual(control['observed_local_targets'],{'Helper.Transfer':False,'Client.Target':True})
            else:
                self.assertEqual(changed,list(b.EDITABLE));self.assertTrue(control['strict_workspace_verified'])

    def test_typed_method_interfaces_keep_inputs_and_outputs_distinct(self):
        for task in read('tasks.json'):
            rules=task['file_rules'];self.assertEqual(set(rules),set(b.EDITABLE))
            for filename,rule in rules.items():
                self.assertEqual(rule['variables'],list(rule['parameter_types']))
                self.assertFalse(set(rule['parameter_types']) & set(rule['output_types']))
                self.assertEqual(set(rule['pure']),set(rule['pure_types']))
                self.assertEqual(set(rule['calls']),set(rule['call_types']))
                self.assertEqual(set(rule['calls']),set(rule['call_returns']))
                for name,arity in rule['pure'].items():self.assertEqual(arity,len(rule['pure_types'][name]['arguments']))
            self.assertEqual(rules['Helper.dfy']['calls'],{})
            self.assertEqual(rules['Client.dfy']['call_types']['H.Transfer'],list(rules['Helper.dfy']['parameter_types'].values()))
            self.assertEqual(rules['Client.dfy']['call_returns']['H.Transfer'],rules['Helper.dfy']['output_types']['r'])
            self.assertFalse(task['held_out']);self.assertFalse(task['reserved_families_used'])

    def test_arithmetic_semantics_fixed_migration_and_modular_counterexamples(self):
        task=read('tasks.json')[0]
        count=legal=violations=0
        for start,length,cap in itertools.product(range(-2,4),range(5),range(-2,4)):
            old=endpoint(start,length,cap)
            paired=cap if start>cap else start+advance(start,length,cap)
            self.assertEqual(old,paired)
            if start<=cap:
                delta=advance(start,length,cap);self.assertTrue(0<=delta<=length)
                self.assertEqual(start+delta,old);legal+=1
                violations+=int(not (0<=old<=length and start+old==endpoint(start,length,cap)))
            count+=1
        self.assertEqual((count,legal),(180,105));self.assertGreater(violations,0)
        helper,call,result=task['counterexamples']
        p=helper['input'];actual=endpoint(**p)
        self.assertEqual(actual,helper['old_body_result']);self.assertEqual(advance(**p),helper['new_expected_result'])
        self.assertNotEqual(p['start']+actual,endpoint(**p))
        p=call['input'];self.assertTrue(p['length']>=0);self.assertGreater(p['start'],p['cap'])
        p=result['input'];self.assertEqual(advance(**p),result['old_caller_public_result'])
        self.assertNotEqual(result['old_caller_public_result'],endpoint(**p))

    def test_map_semantics_fixed_migration_and_modular_counterexamples(self):
        task=read('tasks.json')[1];count=present=0
        for values in itertools.product((None,-1,0,1),repeat=3):
            m={key:value for key,value in zip((-1,0,1),values) if value is not None}
            for key in range(-2,3):
                patch=entry(m,key)
                remaining={x:y for x,y in m.items() if x not in patch}
                self.assertEqual(remaining,erase(m,key))
                if key in m:self.assertEqual(set(patch),{key});present+=1
                count+=1
        self.assertEqual((count,present),(320,144))
        helper,call,result=task['counterexamples'];m=dict(helper['input']['m']);key=helper['input']['key']
        self.assertIn(key,m);self.assertEqual(erase(m,key),dict(helper['old_body_result']))
        self.assertEqual(entry(m,key),dict(helper['new_expected_result']));self.assertNotEqual(erase(m,key),entry(m,key))
        self.assertNotIn(call['input']['key'],dict(call['input']['m']))
        self.assertNotEqual(dict(result['old_caller_remaining']),dict(result['public_expected_remaining']))


if __name__=='__main__':unittest.main(verbosity=2)
