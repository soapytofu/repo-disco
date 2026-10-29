import json,unittest
from pathlib import Path
import guard
ROOT=Path(__file__).resolve().parent
class Diagnostic(unittest.TestCase):
 def setUp(self):self.cases=json.loads((ROOT/'cases.json').read_text())
 def test_all11_admitted_no_other_source_changes(self):
  for c in self.cases:
   parent=ROOT.parent;task=c['task'];p=parent/'model-001'/c['trial_id'];raw=json.loads((p/'response.json').read_text())['text'];original,_=guard.extract(raw,task['editable_files'])
   seeds={f.name:f.read_text() for f in (parent/'frozen-001/tasks'/task['task_id']).glob('*.dfy')}
   candidate={f.name:f.read_text() for f in (ROOT/c['path']).glob('*.dfy')}
   for n,s in candidate.items():self.assertEqual(s,seeds[n] if n not in task['editable_files'] else original[n]+('\n' if not original[n].endswith('\n') else ''))
   guard.validate_files({n:candidate[n] for n in task['editable_files']},seeds,task)
 def test_inline_conditions_are_pure_and_bounded(self):
  t=next(c['task'] for c in self.cases if c['task']['family']=='conditional_preconditions')
  guard.Grammar('assert (if x >= 0 then x else -x) >= 0;',t).sequence()
  guard.Grammar('assert (if x >= 0 then (if y > 0 then y else 0) else 0) >= 0;',t).sequence()
  for body in ['assert (if x >= 0 then assume false else 0) == 0;','assert (if true then End.Direct(x,y) else 0) == 0;','assert (if true then 0 else reveal K.Safe()) == 0;','if true { assume false; }','assert {:axiom} false;']:
   with self.assertRaises(ValueError):guard.Grammar(body,t).sequence()
 def test_contracts_and_noneditable_files_still_protected(self):
  c=self.cases[0];t=c['task'];parent=ROOT.parent
  seeds={p.name:p.read_text() for p in (parent/'frozen-001/tasks'/t['task_id']).glob('*.dfy')}
  files={p.name:p.read_text() for p in (ROOT/c['path']).glob('*.dfy') if p.name in t['editable_files']};n=t['editable_files'][0]
  for old,new in [('ensures','requires'),('induction false','verify false'),('Kernel`Public','Kernel`Internal')]:
   changed=dict(files);changed[n]=changed[n].replace(old,new)
   with self.assertRaises(ValueError):guard.validate_files(changed,seeds,t)
 def test_original_archive_and_freeze_untouched(self):
  import hashlib
  p=ROOT.parent/'frozen-001'
  self.assertEqual(hashlib.sha256((p/'freeze.json').read_bytes()).hexdigest(),'85166dc676861ac7288006668bf5b9eef6c137e01c1daeda6c95946d4995da81')
  for c in self.cases:self.assertEqual(hashlib.sha256((ROOT.parent/'model-001'/c['trial_id']/'response.json').read_bytes()).hexdigest(),c['original_response_sha256'])
if __name__=='__main__':unittest.main()
