"""Construction invariants and mocked staging; zero real verifier/model calls."""
import json,subprocess,sys,unittest
from collections import Counter
from pathlib import Path
import build
ROOT=Path(__file__).resolve().parent
TASKS=json.loads((ROOT/'tasks.json').read_text());CHECKS=json.loads((ROOT/'checks.json').read_text())
class Tests(unittest.TestCase):
 def test_balance_and_counts(self):
  self.assertEqual(len(TASKS),8);self.assertEqual(Counter(c['expected'] for c in CHECKS),{'success':8,'proof_failure':48,'resolution_failure':8})
  self.assertEqual(len({(c['task_id'],c['variant']) for c in CHECKS}),64)
  for family in ['separated_witness','overwrite_delete']:
   self.assertEqual({(t['depth'],t['sharing']) for t in TASKS if t['semantic_instance']==family},{(d,s) for d in ['shallow','deep'] for s in ['shared','separate']})
 def test_exact_sources_and_protected_contracts(self):
  for t in TASKS:
   family=t['semantic_instance'];fixed=build.sources(family,'shallow','shared','reference')
   for c in [c for c in CHECKS if c['task_id']==t['task_id']]:
    files={p.name:p.read_text() for p in (ROOT/c['path']).glob('*.dfy')}
    self.assertEqual(files,build.sources(family,t['depth'],t['sharing'],c['variant']));self.assertEqual(build.hashes(files),c['source_sha256'])
    for n in ['Kernel.dfy','Ops1.dfy','Ops2.dfy','Api.dfy','ClientA.dfy','ClientB.dfy','All.dfy']:self.assertEqual(files[n],fixed[n])
    for n in ['HelperA.dfy','HelperB.dfy']:
     self.assertIn(build.WS if family=='separated_witness' else build.MS,files[n]);self.assertEqual(files[n].count('{'),files[n].count('}'))
    if t['sharing']=='shared':self.assertEqual(files['HelperB.dfy'],fixed['HelperB.dfy'])
 def test_mathematical_distinctions_and_mutations(self):
  self.assertIn('0 < gap',build.WS);self.assertIn('u + gap <= v',build.WK);self.assertNotIn('requires',build.MS)
  for depth in ['shallow','deep']:
   for fn,variants in [(build.wproof,build.WVAR),(build.mproof,build.MVAR)]:
    ref=fn(depth,'reference')
    for v in variants[1:]:self.assertNotEqual(fn(depth,v),ref)
    for forbidden in ['assume','reveal','{:','while']:self.assertNotIn(forbidden,ref)
  self.assertIn('if k == j',build.mproof('deep','reference'));self.assertEqual(build.wproof('deep','reference').count('O2.Join('),2)
 def test_hidden_shortcuts_and_copyable_separate(self):
  for t in TASKS:
   f=build.sources(t['semantic_instance'],t['depth'],t['sharing'],'reference')
   self.assertIn('Api`'+('Deep' if t['depth']=='deep' else 'Shallow'),f['HelperA.dfy'])
   if t['sharing']=='separate':self.assertEqual(f['HelperA.dfy'].replace('module HelperA','module HelperB'),f['HelperB.dfy'])
 def test_isolated_import_fake_staging(self):
  script='''import sys,subprocess
from pathlib import Path
from unittest.mock import patch
root=Path(sys.argv[1]);sys.path.insert(0,str(root));import preflight
checks=preflight.load(root/'checks.json');assert len(checks)==64
sources={p.name:p.read_bytes() for p in (root/checks[0]['path']).glob('*.dfy')}
def fake(command,**kwargs):
 assert command==['timeout','-k','5s','60s','dafny','verify','--verify-included-files','All.dfy']
 assert {p.name:p.read_bytes() for p in Path(kwargs['cwd']).glob('*.dfy')}==sources
 return subprocess.CompletedProcess(command,0,'fake only','')
with patch('subprocess.run',side_effect=fake) as p:
 r=preflight.verify_repository(sources,'All.dfy',60);assert p.call_count==1 and r.evidence['exit_code']==0
'''
  r=subprocess.run([sys.executable,'-I','-B','-c',script,str(ROOT)],capture_output=True,text=True,timeout=20);self.assertEqual(r.returncode,0,r.stdout+r.stderr)
if __name__=='__main__':unittest.main(verbosity=2)
