import json,unittest
from pathlib import Path
R=Path(__file__).resolve().parent
class DesignTests(unittest.TestCase):
 def test_matched_conditions(self):
  for tier in ['diamond','nested']:
   a=R/'fixtures'/f'{tier}_shared_reference';b=R/'fixtures'/f'{tier}_separate_reference'
   for name in ['Facts.dfy','All.dfy','ClientA.dfy']:self.assertEqual((a/name).read_bytes(),(b/name).read_bytes())
   text=(b/'ClientB.dfy').read_text().replace('ViewB','ViewA').replace('LiftB','LiftA').replace('JoinB','JoinA')
   self.assertEqual(text,(a/'ClientB.dfy').read_text())
 def test_negative_controls_preserve_contracts(self):
  for check in json.loads((R/'checks.json').read_text()):
   tier,condition,_=check['variant'].split('_',2);folder=R/'fixtures'/check['variant'];ref=R/'fixtures'/f'{tier}_{condition}_reference'
   self.assertEqual((folder/'Facts.dfy').read_bytes(),(ref/'Facts.dfy').read_bytes())
   for name in ['ClientA.dfy','ClientB.dfy']:
    self.assertEqual((folder/name).read_text().split('  {\n')[0],(ref/name).read_text().split('  {\n')[0])
 def test_check_plan_unique(self):
  checks=json.loads((R/'checks.json').read_text());self.assertEqual(len(checks),76)
  self.assertEqual(len({(c['variant'],c['entry']) for c in checks}),len(checks))
  self.assertEqual(sum(c['expected_exit']==0 for c in checks),12)
if __name__=='__main__':unittest.main()
