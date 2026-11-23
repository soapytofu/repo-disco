"""Synthetic preparation-boundary tests; no mathematical evidence or dispatch."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'execution-001'))
import prepare
from runtime import canonical,sha,TASK_ORDER,native
from test_runner import stages,SETTINGS,scope
from test_allocation import binding_fixture


def put(root,name,value):
    path=root/name;path.parent.mkdir(parents=True,exist_ok=True)
    raw=value if isinstance(value,bytes) else canonical(value)
    path.write_bytes(raw)
    return dict(path=name,sha256=sha(raw))


def fixture(root):
    config=scope();config["batch_id"]="dafny-real-library-growth-002-execution-001"
    _,binding=binding_fixture(root,config,stage_external=False)
    put(root,'execution-001/execution-binding.json',binding)
    for name in ['execution-001/ops.py','execution-001/test_ops.py','execution-001/model.sbatch',
                 'pilot/test_render.py','pilot/prepare.py','pilot/render.py']:
        put(root,name,b'# SYNTHETIC FIXTURE ONLY\n')
    # The binding fixture uses a different frozen input path; preserve exact bytes.
    put(root,'execution-001/budget-snapshot.json',(root/binding['budget_snapshot_input']).read_bytes())
    tasks={};task_gates={}
    for (task,_),stage in stages().items():
        ep=put(root,'inputs/'+task+'/edit.json',stage.edit_profile)
        np=put(root,'inputs/'+task+'/native.json',stage.native_profile)
        bases={name:put(root,'inputs/'+task+'/base/'+name,raw) for name,raw in stage.base_sources.items()}
        tasks[task]=dict(edit_profile=ep,native_profile=np,base_sources=bases,native_adapter=stage.adapter,
                         component='SYNTHETIC',description='SYNTHETIC '+task)
        pins={pin['path']:pin['sha256'] for pin in [ep,np,*bases.values()]}
        task_gates[task]=dict(qualified_success=True,all_controls_match=True,input_files=pins)
    gate=dict(status='PASS',all_expected_match=True,model_calls=0,tasks=task_gates,synthetic_test_fixture=True)
    gp=put(root,'gate.json',gate)
    inputs=dict(schema='dafny-varied-pilot-preparation-v1',tasks=tasks,control_gate=gp,settings=SETTINGS,
                synthetic_test_fixture=True)
    put(root,'inputs.json',inputs)
    return inputs,gate


class PreparationTests(unittest.TestCase):
    def test_exact_bases_and_only_template_are_model_visible(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);inputs,gate=fixture(root)
            with mock.patch.object(prepare,'ROOT',root):result=prepare.prepare(root/'inputs.json',root/'pilot/frozen-001')
            self.assertEqual(result['max_calls'],8)
            actual=json.loads((root/'pilot/frozen-001/scope.json').read_bytes())
            self.assertEqual([s['project'] for s in actual['slots']],list(TASK_ORDER)+list(reversed(TASK_ORDER)))
            for task in TASK_ORDER:
                payload=json.loads((root/'pilot/frozen-001/payloads'/f'{task}.json').read_bytes())
                text=payload['messages'][0]['content'][0]['text']
                self.assertIn('module Base { function Next(x: int): int { x + 1 } }',text)
                self.assertNotIn('SYNTHETIC-REQUEST',text)
                self.assertIn('// BEGIN BODY\n // END BODY',text)
                self.assertNotIn('result := x + 1;',text)

    def test_mixed_task_gate_is_rejected_even_when_profiles_individually_pinned(self):
        for missing in ('edit','native','base'):
            with self.subTest(missing=missing),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);inputs,gate=fixture(root);task=TASK_ORDER[0]
                name=next(k for k in gate['tasks'][task]['input_files'] if '/'+missing in k)
                gate['tasks'][task]['input_files'][name]='f'*64
                inputs['control_gate']=put(root,'gate.json',gate);put(root,'inputs.json',inputs)
                with mock.patch.object(prepare,'ROOT',root),self.assertRaises(native.EvidenceError):
                    prepare.prepare(root/'inputs.json',root/'pilot/frozen-001')

    def test_failed_or_missing_task_controls_cannot_freeze(self):
        for kind in ('aggregate','task','pending'):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);inputs,gate=fixture(root)
                if kind=='aggregate':gate['all_expected_match']=False
                elif kind=='task':gate['tasks'].pop(TASK_ORDER[0])
                else:gate['tasks'][TASK_ORDER[0]]['all_controls_match']=False
                inputs['control_gate']=put(root,'gate.json',gate);put(root,'inputs.json',inputs)
                with mock.patch.object(prepare,'ROOT',root),self.assertRaises(native.EvidenceError):
                    prepare.prepare(root/'inputs.json',root/'pilot/frozen-001')

    def test_source_drift_is_rejected_before_payload_creation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);inputs,gate=fixture(root)
            pin=next(iter(inputs['tasks'][TASK_ORDER[0]]['base_sources'].values()))
            (root/pin['path']).write_bytes(b'changed')
            with mock.patch.object(prepare,'ROOT',root),self.assertRaises(native.EvidenceError):
                prepare.prepare(root/'inputs.json',root/'pilot/frozen-001')
            self.assertFalse((root/'pilot/frozen-001/payloads').exists())

if __name__=='__main__':unittest.main(verbosity=2)
