"""Offline fixture construction tests; no Dafny or model execution."""
from pathlib import Path
import hashlib,json,tempfile,unittest
from unittest.mock import patch
import generate as g
import verify as v
class StructureTests(unittest.TestCase):
 def test_deterministic_complete_matrix(self):
  with tempfile.TemporaryDirectory() as d:
   tasks,cases,manifest=g.build(d)
   self.assertEqual(len(tasks),2);self.assertEqual(len(cases),18)
   self.assertEqual(manifest,json.loads((g.ROOT/'fixture-manifest.json').read_text()))
   self.assertEqual(sum(c['expected']=='success' for c in cases),4)
   self.assertEqual(sum(c['expected']=='proof_failure' for c in cases),12)
   self.assertEqual(sum(c['expected']=='resolution_failure' for c in cases),2)
 def test_mutations_only_inside_editable_proofs(self):
  for sharing in ('shared','separate'):
   base=g.sources(sharing,'');editable=['HelperA.dfy']+(['HelperB.dfy'] if sharing=='separate' else [])
   for body,_,_ in g.VARIANTS.values():
    candidate=g.sources(sharing,body)
    for n,s in candidate.items():
     if n not in editable:self.assertEqual(s,base[n])
     else:
      prefix,suffix=base[n].split('  {\n  }',1)
      self.assertEqual(s,prefix+'  {\n'+body+'  }'+suffix)
 def test_matched_clients_and_contracts(self):
  a=g.sources('shared',g.REFERENCE);b=g.sources('separate',g.REFERENCE)
  for n in ('Kernel.dfy','Ops.dfy','ClientA.dfy','ClientB.dfy','HelperA.dfy','All.dfy'):self.assertEqual(a[n],b[n])
  self.assertIn(g.SIGNATURE,a['HelperB.dfy']);self.assertIn(g.SIGNATURE,b['HelperB.dfy'])
  self.assertEqual(b['HelperA.dfy'].replace('module HelperA','module HelperB'),b['HelperB.dfy'])
 def test_hidden_range_and_opaque_kernel(self):
  self.assertIn('opaque function Sat',g.KERNEL)
  public=g.OPS.split('export Public provides ',1)[1].split('\n',1)[0]
  self.assertNotIn('Range',public);self.assertIn('O.Range',g.VARIANTS['hidden_range'][0])
  for label,(body,_,_) in g.VARIANTS.items():
   self.assertNotRegex(body,r'\b(?:assume|reveal|axiom)\b')
 def test_checker_keeps_categories_distinct(self):
  base=dict(stdout='Dafny program verifier finished with 0 verified, 1 error\n',stderr='',exit_code=4)
  self.assertEqual(v.classify(base),'proof_failure')
  self.assertEqual(v.classify(dict(base,stderr='Error: decreases expression might not decrease')),'termination_failure')
  self.assertEqual(v.classify(dict(base,exit_code=2,stdout='Error: unresolved identifier: Range')),'resolution_failure')
  self.assertEqual(v.classify(dict(base,exit_code=2,stdout='1 parse errors detected')),'other')
 def test_verifier_stages_exact_bytes_with_fake_process(self):
  import types
  files={n:s.encode() for n,s in g.sources('shared',g.REFERENCE).items()};seen=[]
  def fake(command,cwd,capture_output,text):
   seen.append(command);self.assertEqual({p.name:p.read_bytes() for p in Path(cwd).glob('*.dfy')},files)
   (Path(cwd)/'test.csv').write_bytes(b'fake\r\n')
   return types.SimpleNamespace(returncode=0,stdout='FAKE',stderr='')
  with patch.object(v.subprocess,'run',side_effect=fake):record=v.verify(files)
  self.assertEqual(len(seen),1);self.assertEqual(record['csv'],{'test.csv':'fake\r\n'})
  self.assertEqual(record['source_sha256'],g.hashes(g.sources('shared',g.REFERENCE)))
if __name__=='__main__':unittest.main()
