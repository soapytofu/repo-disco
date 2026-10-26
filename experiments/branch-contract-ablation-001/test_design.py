import unittest,json,re
from pathlib import Path
R=Path(__file__).resolve().parent
class DesignTests(unittest.TestCase):
 def test_single_guarantee_mutation(self):
  for folder in (R/'fixtures').iterdir():
   condition,suffix=folder.name.split('_',1);source=R.parent/'sharing-branching-001/fixtures'/f'{condition}_reference'
   for n in ['ClientA.dfy','ClientB.dfy','All.dfy']:self.assertEqual((folder/n).read_bytes(),(source/n).read_bytes())
   old=(source/'Facts.dfy').read_text();new=(folder/'Facts.dfy').read_text()
   if suffix=='reference':self.assertEqual(old,new)
   else:
    expected,count=re.subn(r'(lemma '+suffix+r'\(x: int\)\n    requires [^\n]+\n    ensures )[^\n]+',r'\g<1>true',old)
    self.assertEqual(count,1);self.assertEqual(new,expected)
 def test_unique_controls(self):
  checks=json.loads((R/'checks.json').read_text());self.assertEqual(len(checks),22)
  self.assertEqual(len({(r['variant'],r['entry']) for r in checks}),22)
  self.assertEqual(sum(r['expected_exit']==4 for r in checks),8)
if __name__=='__main__':unittest.main()
