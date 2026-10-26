import json,re,unittest
from pathlib import Path
R=Path(__file__).resolve().parent
class DesignTests(unittest.TestCase):
 def test_clients_and_specs_fixed(self):
  for folder in (R/'fixtures').iterdir():
   condition=folder.name.split('_')[0];ref=R/'fixtures'/f'{condition}_reference'
   for n in ['ClientA.dfy','ClientB.dfy','All.dfy']:self.assertEqual((folder/n).read_bytes(),(ref/n).read_bytes())
   text=(folder/'Facts.dfy').read_text();base=(ref/'Facts.dfy').read_text()
   self.assertEqual(text.split('  lemma')[0],base.split('  lemma')[0])
   self.assertEqual(re.findall(r'  lemma.*?\n  \{',text,re.S),re.findall(r'  lemma.*?\n  \{',base,re.S))
 def test_matched_client_goals_and_automatic_induction_disabled(self):
  a=R/'fixtures/shared_reference';b=R/'fixtures/separate_reference'
  self.assertEqual((a/'ClientA.dfy').read_bytes(),(b/'ClientA.dfy').read_bytes())
  self.assertEqual((a/'ClientB.dfy').read_text(),(b/'ClientB.dfy').read_text().replace('ViewB','ViewA').replace('AppendB','AppendA'))
  for folder in (R/'fixtures').iterdir():
   text=(folder/'Facts.dfy').read_text();expected=1 if folder.name.startswith('shared_') else 2
   self.assertEqual(text.count('{:induction false}'),expected)
 def test_plan(self):
  checks=json.loads((R/'checks.json').read_text());self.assertEqual(len(checks),16)
  self.assertEqual(len({(c['variant'],c['entry']) for c in checks}),16)
  self.assertEqual(sum(c['expected_exit']==0 for c in checks),6)
if __name__=='__main__':unittest.main()
