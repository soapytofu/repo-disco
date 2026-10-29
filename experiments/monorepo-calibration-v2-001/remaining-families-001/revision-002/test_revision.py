import json,unittest
from pathlib import Path
from body_protocol import parse_response
from grammar import split_seed
ROOT=Path(__file__).resolve().parent
class Revision(unittest.TestCase):
 def test_only_trusted_kernel_and_stage3_changed(self):
  for c in json.loads((ROOT/'checks.json').read_text()):
   for p in (ROOT/c['path']).glob('*.dfy'):
    old=ROOT.parent/c['path']/p.name
    if p.name not in ['Kernel.dfy','Stage3.dfy']:self.assertEqual(p.read_bytes(),old.read_bytes())
    else:self.assertNotEqual(p.read_bytes(),old.read_bytes())
   kernel=(ROOT/c['path']/'Kernel.dfy').read_text()
   self.assertIn('Witness(a: int, b: int, c: int, d: int, w: int) { a <= w <= b && c <= w <= d }',kernel)
   self.assertIn('exists w: int {:trigger Witness(a,b,c,d,w)} :: Witness(a,b,c,d,w)',kernel)
 def test_references_guarded_exactly_and_contracts_preserved(self):
  for t in json.loads((ROOT/'tasks.json').read_text()):
   def fs(v):return {p.name:p.read_text() for p in (ROOT/'fixtures'/t['task_id']/v).glob('*.dfy')}
   seed=fs('empty');ref=fs('reference');bodies={}
   for n in t['editable_files']:
    pre,suf=split_seed(seed[n]);self.assertTrue(ref[n].startswith(pre) and ref[n].endswith(suf));bodies[n]=ref[n][len(pre):-len(suf)]
   self.assertEqual(parse_response(json.dumps(bodies),seed,t)[0],ref)
 def test_expected_control_categories_unchanged(self):
  old=[c for c in json.loads((ROOT.parent/'checks.json').read_text()) if c['task_id'].startswith('witness-')];new=json.loads((ROOT/'checks.json').read_text())
  self.assertEqual([(c['task_id'],c['variant'],c['expected']) for c in old],[(c['task_id'],c['variant'],c['expected']) for c in new]);self.assertEqual(len(new),30)
if __name__=='__main__':unittest.main()
