import json,unittest
from pathlib import Path
from body_protocol import parse_response
from grammar import split_seed
ROOT=Path(__file__).resolve().parent
class Revision(unittest.TestCase):
 def test_only_ghost_modifier_changed_from_revision002(self):
  for c in json.loads((ROOT/'checks.json').read_text()):
   for p in (ROOT/c['path']).glob('*.dfy'):
    old=(ROOT.parent/'revision-002'/c['path']/p.name).read_text()
    expected=old.replace('opaque predicate Overlap(','opaque ghost predicate Overlap(') if p.name=='Kernel.dfy' else old
    self.assertEqual(p.read_text(),expected)
 def test_references_exactly_roundtrip_and_original_client_contracts_unchanged(self):
  for t in json.loads((ROOT/'tasks.json').read_text()):
   def fs(v):return {p.name:p.read_text() for p in (ROOT/'fixtures'/t['task_id']/v).glob('*.dfy')}
   seed=fs('empty');ref=fs('reference');bodies={}
   for n in t['editable_files']:
    pre,suf=split_seed(seed[n]);bodies[n]=ref[n][len(pre):-len(suf)]
   self.assertEqual(parse_response(json.dumps(bodies),seed,t)[0],ref)
   for n in ['HelperA.dfy','HelperB.dfy','ClientA.dfy','ClientB.dfy']:
    self.assertEqual(ref[n],(ROOT.parent/'fixtures'/t['task_id']/'reference'/n).read_text())
 def test_30_control_expectations_unchanged(self):
  old=json.loads((ROOT.parent/'revision-002/checks.json').read_text());new=json.loads((ROOT/'checks.json').read_text())
  self.assertEqual([(c['task_id'],c['variant'],c['expected']) for c in old],[(c['task_id'],c['variant'],c['expected']) for c in new]);self.assertEqual(len(new),30)
if __name__=='__main__':unittest.main()
