import json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
class DesignTests(unittest.TestCase):
 def test_matched_conditions(self):
  a=ROOT/'fixtures/shared_reference';b=ROOT/'fixtures/separate_reference'
  for name in ['All.dfy','Facts.dfy','ClientA.dfy']:self.assertEqual((a/name).read_bytes(),(b/name).read_bytes())
  self.assertEqual((a/'ClientB.dfy').read_text(),(b/'ClientB.dfy').read_text().replace('ViewB','ViewA').replace('Case0B','Case0A').replace('Case1B','Case1A'))
 def test_protected_sources(self):
  for folder in (ROOT/'fixtures').iterdir():
   ref=ROOT/'fixtures'/(folder.name.split('_')[0]+'_reference')
   self.assertEqual((folder/'Facts.dfy').read_bytes(),(ref/'Facts.dfy').read_bytes())
   for name in ['ClientA.dfy','ClientB.dfy']:self.assertEqual((folder/name).read_text().split('  {\n')[0],(ref/name).read_text().split('  {\n')[0])
 def test_control_plan(self):
  checks=json.loads((ROOT/'checks.json').read_text());self.assertEqual(len(checks),34)
  self.assertEqual(len({(r['variant'],r['entry']) for r in checks}),34)
  self.assertEqual(sum(r['expected_exit']==0 for r in checks),6)
if __name__=='__main__':unittest.main()
