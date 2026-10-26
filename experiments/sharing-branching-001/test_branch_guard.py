import json,unittest
from pathlib import Path
from branch_guard import parse_response,validate_body
ROOT=Path(__file__).resolve().parent
class BranchGuardTests(unittest.TestCase):
 def originals(self,condition='shared'):
  return {n:(ROOT/'fixtures'/f'{condition}_empty'/n).read_text() for n in ['ClientA.dfy','ClientB.dfy']}
 def test_reference_and_negative_fixtures_are_syntactic(self):
  for folder in (ROOT/'fixtures').iterdir():
   originals=self.originals(folder.name.split('_')[0]);files={n:(folder/n).read_text() for n in originals}
   self.assertEqual(parse_response(json.dumps(files),originals)[0],files)
 def test_wrappers_exact_preservation(self):
  originals=self.originals();files={n:(ROOT/'fixtures/shared_reference'/n).read_text() for n in originals}
  for before,after in [('', ''),('Proof:\n',''),('```json\n','\n```'),('prose {\n','\nDone.')]:
   self.assertEqual(parse_response(before+json.dumps(files)+after,originals)[0],files)
 def test_equivalent_structures_syntactic(self):
  for body in ['if x < 0 { F.Case1A(x); } else { F.Case0A(x); }','if 0 <= x { F.Case0A(x); } else { F.Case1A(x); }','if x < 0 { F.Case1A(x); } else if x == 0 { F.Case0A(x); } else { F.Case0A(x); }','if x-y >= 0 { F.Case0B((x-y)); } else { F.Case1B(x-y); }']:
   self.assertTrue(validate_body(body))
 def test_forbidden_constructs(self):
  for body in ['assume false;','assert true;','reveal F.Good();','while true {}','{:verify false}','F.Case0A(x); // comment','F.Case0A(x); /* comment */','F.Case0A(x); lemma Evil() {}','F.Case0A(x,y);','F.Case0A(z);','F.Case0A(F.Wrap(x));','F.Case0A(x*2);','if * { F.Case0A(x); }','if x>=0 F.Case0A(x);','if x>=0 {F.Case0A(x);','F.Case0A(x); }','F.Case0A(x) garbage','F.Unknown(x);','if x>=0 && y>=0 {}']:
   with self.subTest(body=body),self.assertRaises(ValueError):validate_body(body)
 def test_protected_edits(self):
  originals=self.originals();files={n:(ROOT/'fixtures/shared_reference'/n).read_text() for n in originals}
  for changed in [files['ClientA.dfy'].replace('ensures F.Good','ensures true || F.Good'),files['ClientA.dfy'].replace('ViewA','ViewB'),files['ClientA.dfy'].replace('x: int','x: nat')]:
   with self.assertRaises(ValueError):parse_response(json.dumps({**files,'ClientA.dfy':changed}),originals)
 def test_json_ambiguity_and_schema(self):
  raw=json.dumps(self.originals())
  for bad in [raw+raw,'{}'+raw,raw[:-1],'{"ClientA.dfy":"a","ClientA.dfy":"b","ClientB.dfy":"c"}',json.dumps({**self.originals(),'Facts.dfy':'bad'}),json.dumps({'ClientA.dfy':42,'ClientB.dfy':'x'})]:
   with self.assertRaises(ValueError):parse_response(bad,self.originals())
 def test_resource_bounds(self):
  for body in ['F.Case0A(x);'*65,'F.Case0A('+'('*30+'x'+')'*30+');','if x>=0 {'*30+'}'*30,'F.Case0A(1234567890123);']:
   with self.assertRaises(ValueError):validate_body(body)
if __name__=='__main__':unittest.main()
