"""Offline diagnostics and policy tests; fake processes only, no model clients."""
import ast
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
from prepare import ROOT, load, files, hashes, module

guard=module('diagnostic_guard',ROOT/'policy/body_guard.py')
old=module('frozen_guard',ROOT/'policy/old_body_guard.py')
envelope=module('diagnostic_envelope',ROOT/'policy/extract_response.py')
TASKS={t['task_id']:t for t in load(ROOT/'tasks.json')}

def parse(raw,task,policy=guard,seed=None):
    return envelope.parse_response(raw,seed or files(ROOT/'seeds'/task['task_id']),task,policy)

def sample(body):
    task=TASKS['map_swap-shallow-shared']
    return parse(json.dumps({'HelperA.dfy':body}),task)

class Tests(unittest.TestCase):
    def test_exact_six_analyst_edits_and_original_parser_response(self):
        checks=load(ROOT/'checks.json');cases=load(ROOT/'cases.json');self.assertEqual(len(checks),6)
        self.assertEqual([c['expected'] for c in checks].count('success'),3)
        for case,check in zip(cases,checks):
            task=TASKS[case['task_id']];parent=ROOT/'parents'/case['source_trial']
            raw=(ROOT/'responses'/case['variant']/'body.json').read_text()
            policy=old if case['variant'].startswith('deep_') else guard
            candidate,decision=parse(raw,task,policy)
            self.assertEqual(candidate,files(ROOT/check['path']))
            self.assertEqual(hashes(candidate),check['source_sha256'])
            self.assertEqual(decision,load(ROOT/'responses'/case['variant']/'extraction.json'))
            if case['variant']=='quantifier_original':
                self.assertEqual(raw,load(parent/'response.json')['text'])
                with self.assertRaisesRegex(ValueError,'Unknown expression name'):parse(raw,task,old)
            if case['variant'].startswith('deep_'):
                bodies=json.loads(raw);original=json.loads(envelope.extract_json(load(parent/'response.json')['text'])[0])
                keys=('k','j') if case['variant'].endswith('both') else (('k',) if case['variant'].endswith('k_only') else ('j',))
                for name,body in bodies.items():
                    addition=''.join(f'      O2.SwapAt(m, k, j, {k});\n' for k in keys)
                    self.assertEqual(body,original[name].replace('      O2.SwapAt(m, k, j, q);',addition+'      O2.SwapAt(m, k, j, q);'))

    def test_all_32_saved_responses_exact_replay(self):
        count=old_accepted=0
        for parent in sorted((ROOT/'parents').glob('varied-cal-*')):
            task=load(parent/'task.json');raw=load(parent/'response.json')['text']
            expected=load(parent/'extraction.json')
            candidate,decision=parse(raw,task)
            bodies=json.loads(envelope.extract_json(raw)[0]);seed=files(ROOT/'seeds'/task['task_id'])
            for name in seed:
                if name in task['editable_files']:
                    a,b=old.split_seed(seed[name]);self.assertEqual(candidate[name],a+bodies[name]+b)
                else:self.assertEqual(candidate[name],seed[name])
            if expected['accepted']:
                previous,old_decision=parse(raw,task,old)
                self.assertEqual(candidate,previous);self.assertEqual(previous,files(parent/'candidate'))
                self.assertEqual(old_decision['body_guard'],expected['body_guard']);old_accepted+=1
                equivalent=dict(decision['body_guard']);equivalent['version']=old.VERSION
                self.assertEqual(equivalent,old_decision['body_guard'])
            else:
                self.assertEqual(parent.name,'varied-cal-27')
                with self.assertRaises(ValueError):parse(raw,task,old)
            count+=1
        self.assertEqual((count,old_accepted),(32,31))

    def test_110_semantic_controls_and_16_hidden_export_rejections(self):
        accepted=rejected=0
        for c in load(ROOT/'control-replays.json'):
            task=TASKS[c['task_id']];raw=json.dumps(c['bodies'])
            if c['admitted']:
                candidate,new=parse(raw,task);previous,_=parse(raw,task,old)
                self.assertEqual(candidate,previous);self.assertEqual(hashes(candidate),c['source_sha256']);accepted+=1
            else:
                with self.assertRaises(ValueError):parse(raw,task)
                rejected+=1
        self.assertEqual((accepted,rejected),(110,16))

    def test_quantifier_scope_boundaries_and_negative_truth(self):
        for body in [
            'assert forall q :: q == q;',
            'assert (forall q :: q in m ==> m[q] == m[q]);',
            'assert forall q :: (forall r :: q == r ==> r == q);',
            'assert forall q :: q == q; assert forall q :: q == q;',
            'assert forall q :: q == 0;',
            'forall q | q in m ensures q in m { assert forall r :: r == r; }',
        ]:sample(body)
        for body in [
            'assert forall m :: true;', 'assert forall K :: true;',
            'assert forall A :: true;', 'assert forall O1 :: true;',
            'assert forall Prove :: true;', 'assert forall q :: (forall q :: true);',
            'assert forall q :: true; assert q == 0;',
            'var q := 0; assert forall q :: true;',
            'assert forall q, r :: true;', 'assert forall q: int :: true;',
            'assert forall q {:trigger q} :: true;', 'assert forall q :: assume false;',
            'assert forall q :: H.Prove();', 'assert forall q :: A.ObserveSwap(m,k,j);',
            'assert forall q :: unknown == q;', 'assert forall q :: ;',
        ]:
            with self.assertRaises(ValueError,msg=body):sample(body)
        nested=''.join(f'forall q{i} :: (' for i in range(40))+'true'+')'*40
        with self.assertRaisesRegex(ValueError,'Expression nesting'):sample('assert '+nested+';')

    def test_immutable_inputs_edit_scope_and_envelope_protections(self):
        attacks=['assume false;','assert {:axiom} false;','reveal K.Swap();',
                 'lemma Added() {}','while true {}','HelperA.Prove();',
                 'import K = Kernel`Internal;','return;']
        for body in attacks:
            with self.assertRaises(ValueError):sample(body)
        for task in TASKS.values():
            seed=files(ROOT/'seeds'/task['task_id']);raw=json.dumps({n:'' for n in task['editable_files']})
            for name in seed:
                with self.assertRaises(ValueError):parse(raw,task,seed={**seed,name:seed[name]+'\n'})
            with self.assertRaises(ValueError):parse(raw+'\n'+raw,task)
            with self.assertRaises(ValueError):parse(json.dumps({'answer':json.loads(raw)}),task)
        with self.assertRaises(ValueError):sample('assert true;'*257)
        with self.assertRaises(ValueError):sample(' '*(guard.MAX_BODY+1))

    def test_only_scoped_atom_and_version_policy_changes(self):
        a=ast.parse((ROOT/'policy/old_body_guard.py').read_text())
        b=ast.parse((ROOT/'policy/body_guard.py').read_text())
        def atom(tree):
            return next(n for c in tree.body if isinstance(c,ast.ClassDef) and c.name=='Grammar' for n in c.body if isinstance(n,ast.FunctionDef) and n.name=='atom')
        old_atom,new_atom=atom(a),atom(b)
        # Locate the single added forall branch, then remove it from the copy.
        conditions=[n for n in ast.walk(new_atom) if isinstance(n,ast.If) and ast.dump(n.test,include_attributes=False)==ast.dump(ast.parse("token=='forall'",mode='eval').body,include_attributes=False)]
        self.assertEqual(len(conditions),1);added=conditions[0]
        for n in ast.walk(new_atom):
            if isinstance(n,ast.If) and n.orelse and n.orelse[0] is added:n.orelse=added.orelse;break
        self.assertEqual(ast.dump(old_atom,include_attributes=False),ast.dump(new_atom,include_attributes=False))
        for tree in (a,b):
            tree.body=[n for n in tree.body if not (isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='VERSION' for t in n.targets))]
        self.assertEqual(ast.dump(a,include_attributes=False),ast.dump(b,include_attributes=False))

    def test_isolated_verifier_and_remote_script_syntax(self):
        sys.path.insert(0,str(ROOT/'code'))
        from language.dafny import repository
        self.assertTrue(Path(repository.__file__).is_relative_to(ROOT/'code'))
        seed={n:s.encode() for n,s in files(ROOT/'fixtures/deep_shared_both').items()}
        def process(command,cwd,capture_output,text):
            self.assertEqual({p.name:p.read_bytes() for p in Path(cwd).glob('*.dfy')},seed)
            return types.SimpleNamespace(returncode=0,stdout='Dafny program verifier finished with 14 verified, 0 errors\n',stderr='')
        with patch.object(repository.subprocess,'run',side_effect=process):
            evidence=repository.verify_repository(seed,'All.dfy',timeout=60).evidence
        self.assertEqual(evidence['attempts'],1)
        from preflight import diagnostic
        self.assertEqual(diagnostic(evidence),'success')
        self.assertNotEqual(diagnostic({**evidence,'stdout':evidence['stdout']+'Warning: unsafe'}),'success')
        tree=ast.parse((ROOT/'ops.py').read_text())
        for node in ast.walk(tree):
            if isinstance(node,ast.Constant) and isinstance(node.value,str) and node.value.startswith('import '):
                compile(node.value.replace('REMOTE_ROOT',repr('formal-disco/outputs/map-swap-diagnostic-001')),'remote-snippet','exec')

if __name__=='__main__':unittest.main(verbosity=2)
