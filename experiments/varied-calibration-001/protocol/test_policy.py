"""Exact reconstruction and adversarial output tests; zero model/verifier calls."""
import ast,hashlib,json,unittest
from pathlib import Path
import body_guard as guard
import extract_response

ROOT=Path(__file__).resolve().parent
TASKROOT=ROOT.parent/'revision-002'
EXP=ROOT.parent.parent
TASKS=json.loads((TASKROOT/'tasks.json').read_text())
CHECKS=json.loads((TASKROOT/'checks.json').read_text())

def sources(path):return {p.name:p.read_text() for p in path.glob('*.dfy')}
def payload(task,variant):
    seed=sources(TASKROOT/'fixtures'/task['task_id']/'empty')
    target=sources(TASKROOT/'fixtures'/task['task_id']/variant)
    bodies={}
    for name in task['editable_files']:
        pre,suf=guard.split_seed(seed[name])
        assert target[name].startswith(pre) and target[name].endswith(suf)
        bodies[name]=target[name][len(pre):-len(suf)]
    return seed,target,bodies

def parse(raw,seed,task):return extract_response.parse_response(raw,seed,task,guard)

class Tests(unittest.TestCase):
    def test_reuse_unchanged_grammar_and_envelope(self):
        def stable(p):
            tree=ast.parse(p.read_text())
            tree.body=[n for n in tree.body if not (isinstance(n,ast.FunctionDef) and n.name=='policy') and not (isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='VERSION' for t in n.targets))]
            return ast.dump(tree,include_attributes=False)
        self.assertEqual(stable(ROOT/'body_guard.py'),stable(EXP/'monorepo-policy-integration-001/body_guard.py'))
        self.assertEqual((ROOT/'extract_response.py').read_bytes(),(EXP/'reasoning-envelope-policy-001/extract_response.py').read_bytes())

    def test_110_exact_current_reference_and_negative_reconstructions(self):
        rows=[]
        for c in CHECKS:
            if c['expected']=='resolution_failure':continue
            task=next(t for t in TASKS if t['task_id']==c['task_id'])
            seed,target,bodies=payload(task,c['variant'])
            raw='Here is the proof.\n```json\n'+json.dumps(bodies)+'\n```\nEnd of response.'
            actual,decision=parse(raw,seed,task)
            self.assertEqual(actual,target)
            self.assertEqual(decision['body_guard']['candidate_sha256'],c['source_sha256'])
            rows.append(dict(task_id=c['task_id'],variant=c['variant'],expected=c['expected'],source_sha256=c['source_sha256'],payload_sha256=guard.digest(json.dumps(bodies)),exact=True))
        self.assertEqual(len(rows),110)
        (ROOT/'replay-audit.json').write_text(json.dumps(dict(model_calls=0,verifier_calls=0,exact_reconstructions=len(rows),rows=rows),indent=2)+'\n')

    def test_16_hidden_exports_rejected(self):
        for task in TASKS:
            seed,_,bodies=payload(task,'hidden_shortcut')
            with self.assertRaises(ValueError):parse(json.dumps(bodies),seed,task)

    def test_contract_dependency_and_edit_set_protection(self):
        for task in TASKS:
            seed,_,bodies=payload(task,'reference');name=task['editable_files'][0]
            for fixed in seed:
                if fixed not in task['editable_files']:
                    with self.assertRaises(ValueError):parse(json.dumps(bodies),{**seed,fixed:seed[fixed]+'\n'},task)
            for changed in [seed[name].replace('ensures','ensures true\n    ensures',1),seed[name].replace('{:induction false}','{:induction true}'),seed[name].replace('lemma ','lemma {:verify false} ',1)]:
                with self.assertRaises(ValueError):parse(json.dumps(bodies),{**seed,name:changed},task)
            if task['semantic_instance']=='prefix_split':
                with self.assertRaises(ValueError):parse(json.dumps(bodies),{**seed,name:seed[name].replace('decreases i','decreases *')},task)
            for response in [{**bodies,'Kernel.dfy':'module Kernel {}'},dict(list(bodies.items())[1:]),{**bodies,name:[]},{'files':bodies}]:
                with self.assertRaises(ValueError):parse(json.dumps(response),seed,task)

    def test_bypasses_shadowing_and_wrong_calls_rejected(self):
        attacks=['assume false;','expect true;','reveal K.Swap();','assert {:axiom} false;','assert {:verify false} true;',
            'while true {}','lemma New() {}','import K = Kernel`Internal;','include "other.dfy";',
            'var K := 0;','var A := 0;','var O1 := 0;','var O2 := 0;','var Prove := 0;',
            'H.Prove();','HelperA.Prove();','A.Unknown();','A.Equal();','return;']
        for task in TASKS:
            seed,_,bodies=payload(task,'reference');name=task['editable_files'][0]
            for bad in attacks+['var '+guard.policy(task)['variables'][0]+' := 0;']:
                with self.assertRaises(ValueError,msg=(task['task_id'],bad)):parse(json.dumps({**bodies,name:bad}),seed,task)
            if task['semantic_instance']!='prefix_split':
                with self.assertRaises(ValueError):parse(json.dumps({**bodies,name:'Prove('+','.join(guard.policy(task)['variables'])+');'}),seed,task)

    def test_ambiguous_malformed_or_duplicate_json_rejected(self):
        task=TASKS[0];seed,_,bodies=payload(task,'reference');raw=json.dumps(bodies);name=task['editable_files'][0]
        duplicate='{'+json.dumps(name)+':'+json.dumps(bodies[name])+','+json.dumps(name)+':'+json.dumps(bodies[name])+'}'
        for bad in [raw+'\n'+raw,json.dumps({'answer':bodies}),json.dumps([bodies]),raw[:-1],duplicate,
                    '```json\n{"wrong":\n```\n'+raw,raw+'\n{}',json.dumps({name:float('nan')})]:
            with self.assertRaises(ValueError):parse(bad,seed,task)

    def test_whitespace_fences_and_prose_preserve_body_bytes(self):
        for task in TASKS:
            seed,target,bodies=payload(task,'reference');raw=json.dumps(bodies)
            for envelope in [raw,'  '+raw+'\n','```json\n'+raw+'\n```','Explanation.\n'+raw+'\nDone.']:
                actual,decision=parse(envelope,seed,task);self.assertEqual(actual,target)
                self.assertFalse(decision['body_guard']['semantic_verification_performed'])

    def test_limits_and_statement_truth_remain_separate(self):
        task=TASKS[0];seed,_,bodies=payload(task,'reference');name=task['editable_files'][0]
        for bad in [' '*(guard.MAX_BODY+1),'assert true;'*(guard.MAX_STATEMENTS+1),'if true {'*26+'}'*26]:
            with self.assertRaises(ValueError):parse(json.dumps({**bodies,name:bad}),seed,task)
        # False assertions and missing proofs must reach the verifier, not be mislabeled as formatting errors.
        for text in ['','assert false;']:
            actual,_=parse(json.dumps({**bodies,name:text}),seed,task);self.assertIn(text,actual[name])

if __name__=='__main__':unittest.main(verbosity=2)
