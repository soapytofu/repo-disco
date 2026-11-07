"""Reuse the unchanged grammar, only register the two new semantic instances."""
import ast,hashlib,importlib.util,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent;TASKROOT=ROOT.parent;EXP=TASKROOT.parent
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(EXP/'reasoning-envelope-policy-001'))
import body_guard as guard
import extract_response
TASKS=json.loads((TASKROOT/'tasks.json').read_text());CHECKS=json.loads((TASKROOT/'checks.json').read_text())
def files(path):return {p.name:p.read_text() for p in path.glob('*.dfy')}
def body(seed,candidate):
 pre,suf=guard.split_seed(seed);assert candidate.startswith(pre) and candidate.endswith(suf)
 return candidate[len(pre):-len(suf)]
def payload(t,variant):
 seed=files(TASKROOT/'fixtures'/t['task_id']/'empty');source=files(TASKROOT/'fixtures'/t['task_id']/variant)
 return seed,source,{n:body(seed[n],source[n]) for n in t['editable_files']}
class Tests(unittest.TestCase):
 def test_only_registry_and_version_differ_from_frozen_grammar(self):
  def stable(path):
   tree=ast.parse(path.read_text());tree.body=[n for n in tree.body if not (isinstance(n,ast.FunctionDef) and n.name=='policy') and not (isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='VERSION' for t in n.targets))]
   return ast.dump(tree,include_attributes=False)
  self.assertEqual(stable(ROOT/'body_guard.py'),stable(EXP/'monorepo-policy-integration-001/body_guard.py'))
 def test_all_reference_and_semantic_negative_bytes(self):
  count=0
  for c in CHECKS:
   if c['expected']=='resolution_failure':continue
   t=next(t for t in TASKS if t['task_id']==c['task_id']);seed,expected,bodies=payload(t,c['variant'])
   actual,decision=extract_response.parse_response('Reasoning omitted.\n```json\n'+json.dumps(bodies)+'\n```\nEnd.',seed,t,guard)
   self.assertEqual(actual,expected);self.assertEqual(decision['body_guard']['candidate_sha256'],c['source_sha256']);count+=1
  self.assertEqual(count,56)
 def test_hidden_export_calls_are_rejected(self):
  for t in TASKS:
   seed,_,bodies=payload(t,'hidden_shortcut')
   with self.assertRaises(ValueError):extract_response.parse_response(json.dumps(bodies),seed,t,guard)
 def test_scope_contract_and_bypass_rejections(self):
  for t in TASKS:
   seed,_,bodies=payload(t,'reference');name=t['editable_files'][0]
   for bad in ['assume false;','reveal K.Room();','assert {:axiom} false;','while true {}','Prove(m,k,j,x,y);','var O1 := 0;','var A := 0;','import K = Kernel`Internal;','lemma New() {}']:
    with self.assertRaises(ValueError):extract_response.parse_response(json.dumps({**bodies,name:bad}),seed,t,guard)
   with self.assertRaises(ValueError):extract_response.parse_response(json.dumps(bodies),{**seed,'ClientA.dfy':seed['ClientA.dfy']+'\n'},t,guard)
   with self.assertRaises(ValueError):extract_response.parse_response(json.dumps({**bodies,'Kernel.dfy':'x'}),seed,t,guard)
 def test_competing_and_nested_payloads_never_selected(self):
  for t in TASKS:
   seed,_,bodies=payload(t,'reference');raw=json.dumps(bodies)
   for bad in [raw+'\n'+raw,json.dumps({'answer':bodies}),json.dumps([bodies]),raw[:-1]]:
    with self.assertRaises(ValueError):extract_response.parse_response(bad,seed,t,guard)
if __name__=='__main__':unittest.main(verbosity=2)
