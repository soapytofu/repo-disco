import json,unittest
from pathlib import Path
from parser import parse_response,extract,MAX_BYTES
ROOT=Path(__file__).resolve().parent
class ParserTests(unittest.TestCase):
 def setUp(self):
  self.orig={n:(ROOT/'fixtures/diamond_shared_empty'/n).read_text() for n in ['ClientA.dfy','ClientB.dfy']}
  self.files={n:(ROOT/'fixtures/diamond_shared_reference'/n).read_text() for n in self.orig}
  self.raw=json.dumps(self.files)
 def test_wrappers_preserve_content(self):
  for pre,post in [('',''),('Explanation\n',''),('```json\n','\n```'),('Here is the proof:\n```json\n','\n```\nDone.'),('A brace { in prose\n','')]:
   with self.subTest(pre=pre):self.assertEqual(parse_response(pre+self.raw+post,self.orig)[0],self.files)
 def test_ambiguity_and_malformed(self):
  bad=[self.raw+self.raw,'{}'+self.raw,'{"ClientA.dfy":"x","ClientA.dfy":"y","ClientB.dfy":"z"}',self.raw[:-1],json.dumps({'ClientA.dfy':'x'}),json.dumps({**self.files,'Facts.dfy':'x'}),json.dumps({**self.files,'ClientA.dfy':12}),'x'*(MAX_BYTES+1)]
  for raw in bad:
   with self.subTest(size=len(raw)):
    with self.assertRaises(ValueError):parse_response(raw,self.orig)
 def test_protected_bytes_and_injection(self):
  a=self.files['ClientA.dfy']
  bad=[a.replace('requires F.Value(s) > k','requires true'),a.replace('Facts`ViewA','Facts`ViewB'),a.replace('F.LiftA(s);','assume false;'),a.replace('F.LiftA(s);','assert true;'),a.replace('F.LiftA(s);','reveal F.Value();'),a.replace('F.LiftA(s);','F.LiftA(s); // comment'),a.replace('F.LiftA(s);','F.LiftA(F.Evil(s));')]
  for text in bad:
   with self.subTest(text=text):
    with self.assertRaises(ValueError):parse_response(json.dumps({**self.files,'ClientA.dfy':text}),self.orig)
 def test_all_references_and_empty_guard(self):
  for tier in ['diamond','nested']:
   for condition in ['shared','separate']:
    orig={n:(ROOT/'fixtures'/f'{tier}_{condition}_empty'/n).read_text() for n in self.orig}
    ref={n:(ROOT/'fixtures'/f'{tier}_{condition}_reference'/n).read_text() for n in self.orig}
    self.assertEqual(parse_response(json.dumps(ref),orig)[0],ref)
    self.assertEqual(parse_response(json.dumps(orig),orig)[0],orig) # Dafny, not parser, judges correctness.
 def test_saved_eight_responses_regression(self):
  old=ROOT.parent/'sharing-model-pilot-001'
  for folder in sorted((old/'model-001').glob('[0-9][0-9]-*')):
   raw=json.loads((folder/'response.json').read_text())['text'];condition=folder.name.split('-')[1]
   orig={n:(old/'fixtures'/f'{condition}_missing'/n).read_text() for n in self.orig}
   files,meta=parse_response(raw,orig)
   expected=json.loads((ROOT.parent/'sharing-extraction-diagnostic-001/extracted'/folder.name/'response.json').read_text())
   self.assertEqual(files,{k:v.strip()+'\n' for k,v in expected.items()})
if __name__=='__main__':unittest.main()
