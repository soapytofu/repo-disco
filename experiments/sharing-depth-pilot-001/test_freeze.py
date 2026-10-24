import importlib.util,json,shutil,tempfile,unittest
from pathlib import Path
from validate import validate,ROOT
class FreezeTests(unittest.TestCase):
 def test_bundle(self):self.assertEqual(validate()['trials'],8)
 def test_tamper_rejected(self):
  for name in ['plan.json','protocol.json','parser.py','prompts/diamond_shared.json','fixtures/nested_separate/ClientB.dfy']:
   with self.subTest(name=name),tempfile.TemporaryDirectory() as d:
    target=Path(d)/'pilot';shutil.copytree(ROOT,target,ignore=shutil.ignore_patterns('__pycache__'))
    p=target/name;p.write_bytes(p.read_bytes()+b' ')
    with self.assertRaises(ValueError):validate(target)
 def test_unchanged_verified_sources_and_parser(self):
  old=ROOT.parent/'sharing-composition-002'
  self.assertEqual((ROOT/'parser.py').read_bytes(),(old/'parser.py').read_bytes())
  spec=importlib.util.spec_from_file_location('frozen_parser',ROOT/'parser.py');parser=importlib.util.module_from_spec(spec);spec.loader.exec_module(parser)
  for tier in ['diamond','nested']:
   for condition in ['shared','separate']:
    cell=f'{tier}_{condition}'
    for p in (ROOT/'fixtures'/cell).glob('*.dfy'):self.assertEqual(p.read_bytes(),(old/'fixtures'/f'{cell}_empty'/p.name).read_bytes())
    originals={n:(ROOT/'fixtures'/cell/n).read_text() for n in parser.CLIENTS}
    reference={n:(old/'fixtures'/f'{cell}_reference'/n).read_text() for n in parser.CLIENTS}
    recovered,_=parser.parse_response('Proof:\n```json\n'+json.dumps(reference)+'\n```',originals)
    self.assertEqual(recovered,reference)
if __name__=='__main__':unittest.main()
