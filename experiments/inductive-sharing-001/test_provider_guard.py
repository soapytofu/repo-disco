import json,unittest
from pathlib import Path
from provider_guard import parse_response,Grammar
R=Path(__file__).resolve().parent/'revision-003/fixtures'
class ProviderGuardTests(unittest.TestCase):
 def wrap(self,text):return 'Proof:\n```json\n'+json.dumps({'Facts.dfy':text})+'\n```'
 def test_every_verified_control_preserved(self):
  for folder in R.iterdir():
   source=(folder/'Facts.dfy').read_text();original=(R/(folder.name.split('_')[0]+'_empty')/'Facts.dfy').read_text()
   self.assertEqual(parse_response(self.wrap(source),original)[0],source)
 def test_protected_edits(self):
  original=(R/'shared_empty/Facts.dfy').read_text();ref=(R/'shared_reference/Facts.dfy').read_text()
  for text in [ref.replace('induction false','induction true'),ref.replace('decreases |s|','decreases *'),ref.replace('ensures Total(s + t) == Total(s) + Total(t)','ensures true'),ref.replace('provides Total','reveals Total'),ref.replace('then 0 else','then 1 else'),ref.replace('AppendA(s[1..], t);','assume false;'),ref.replace('AppendA(s[1..], t);','reveal Total();'),ref.replace('AppendA(s[1..], t);','assert false;'),ref.replace('AppendA(s[1..], t);','// comment\n      AppendA(s[1..], t);')]:
   with self.subTest(text=text),self.assertRaises(ValueError):parse_response(self.wrap(text),original)
 def test_cross_helper_calls_rejected(self):
  original=(R/'separate_empty/Facts.dfy').read_text();ref=(R/'separate_reference/Facts.dfy').read_text().replace('AppendB(s[1..], t);','AppendA(s[1..], t);')
  with self.assertRaises(ValueError):parse_response(self.wrap(ref),original)
 def test_prior_extra_brace_bug_rejected(self):
  bad=(R.parent.parent/'revision-002/fixtures/shared_reference/Facts.dfy').read_text();original=(R/'shared_empty/Facts.dfy').read_text()
  with self.assertRaises(ValueError):parse_response(self.wrap(bad),original)
 def test_malformed_and_resource_bounds(self):
  for body in ['while true {}','{:axiom}','AppendA(s);','assert s == []; }','if |s| > 0 {','AppendA(s,t);'*65,'assert '+'('*30+'0'+')'*30+' == 0;']:
   with self.subTest(body=body),self.assertRaises(ValueError):Grammar(body,'AppendA').sequence()
 def test_payload_rejects_clients_duplicates_and_ambiguity(self):
  original=(R/'shared_empty/Facts.dfy').read_text()
  for raw in [json.dumps({'Facts.dfy':original,'ClientA.dfy':'bad'}),'{"Facts.dfy":"a","Facts.dfy":"b"}',json.dumps({'Facts.dfy':original})*2]:
   with self.assertRaises(ValueError):parse_response(raw,original)
if __name__=='__main__':unittest.main()
