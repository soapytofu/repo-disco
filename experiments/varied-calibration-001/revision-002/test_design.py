"""Offline construction, boundary and fake-process checks. No live model/Dafny."""
import itertools,json,subprocess,sys,unittest
from collections import Counter
from pathlib import Path
import build
ROOT=Path(__file__).resolve().parent
TASKS=json.loads((ROOT/'tasks.json').read_text());CHECKS=json.loads((ROOT/'checks.json').read_text())
class Tests(unittest.TestCase):
 def test_inventory_and_planning_ids(self):
  self.assertEqual(len(TASKS),16);self.assertEqual(len(CHECKS),126)
  self.assertEqual(Counter(c['expected'] for c in CHECKS),dict(success=16,proof_failure=90,termination_failure=4,resolution_failure=16))
  self.assertEqual(Counter(c['phase'] for c in CHECKS),dict(core=32,negatives=94))
  self.assertEqual(len({(c['task_id'],c['variant']) for c in CHECKS}),126)
  self.assertEqual({t['plan_id'] for t in TASKS},{'D1-C1','D2-C1','D3-C1','D4-C1'})
  for instance in build.DEFS:
   self.assertEqual({(t['depth'],t['sharing']) for t in TASKS if t['semantic_instance']==instance},{(d,s) for d in ['shallow','deep'] for s in ['shared','separate']})
 def test_exact_reconstruction_and_protected_sources(self):
  for t in TASKS:
   ins=t['semantic_instance'];d=build.DEFS[ins];fixed=build.sources(ins,'shallow','shared','reference')
   for c in [c for c in CHECKS if c['task_id']==t['task_id']]:
    fs={f.name:f.read_text() for f in (ROOT/c['path']).glob('*.dfy')}
    self.assertEqual(fs,build.sources(ins,t['depth'],t['sharing'],c['variant']));self.assertEqual(build.hashes(fs),c['source_sha256'])
    for n in ['Kernel.dfy','Ops1.dfy','Ops2.dfy','Api.dfy','ClientA.dfy','ClientB.dfy','All.dfy']:self.assertEqual(fs[n],fixed[n])
    for n in ['HelperA.dfy','HelperB.dfy']:
     self.assertIn(d['signature'],fs[n]);self.assertEqual(fs[n].count('{'),fs[n].count('}'))
    if t['sharing']=='shared':self.assertEqual(fs['HelperB.dfy'],fixed['HelperB.dfy'])
 def test_distinct_mutations_and_no_reference_bypasses(self):
  for ins,d in build.DEFS.items():
   for depth in ['shallow','deep']:
    bodies=[d['proof'](depth,v) for v in d['variants']+(['missing_certificate'] if ins=='map_swap' and depth=='deep' else [])];self.assertEqual(len(bodies),len(set(bodies)),(ins,depth))
    ref=d['proof'](depth,'reference')
    for bad in ['assume','reveal','{:','while']:self.assertNotIn(bad,ref)
 def test_hidden_views_and_separate_copying(self):
  for t in TASKS:
   fs=build.sources(t['semantic_instance'],t['depth'],t['sharing'],'reference')
   self.assertIn('Api`'+('Shallow' if t['depth']=='shallow' else 'Deep'),fs['HelperA.dfy'])
   if t['sharing']=='separate':self.assertEqual(fs['HelperA.dfy'].replace('module HelperA','module HelperB'),fs['HelperB.dfy'])
 def test_small_domain_specification_sanity(self):
  # Finite examples are a specification sanity check, NOT Dafny proof evidence.
  for a,b,c,d,t in itertools.product(range(-2,3),repeat=5):
   if a<=b and c<=d and a+c<=t<=b+d:
    u=max(a,t-d);v=t-u;self.assertTrue(a<=u<=b and c<=v<=d and u+v==t)
  self.assertFalse(1<=3<=2) # a=0,b=2,c=1,d=2,t=3: unconditional u=a makes v=3 invalid.
  for l,h,x,y in itertools.product(range(-2,3),repeat=4):
   if l<=h:
    clamp=lambda z:min(h,max(l,z))
    self.assertLessEqual(abs(clamp(x)-clamp(y)),abs(x-y))
  def swap(m,k,j):
   n=dict(m);n[k],n[j]=m[j],m[k];return n
  for values in itertools.product(range(-1,2),repeat=3):
   m=dict(enumerate(values))
   for k,j in itertools.product(m,repeat=2):self.assertEqual(swap(swap(m,k,j),k,j),m)
  for length in range(4):
   for seq in itertools.product(range(-1,2),repeat=length):
    for i in range(length+1):
     for j in range(length-i+1):self.assertEqual(sum(seq[:i+j]),sum(seq[:i])+sum(seq[i:i+j]))
 def test_error_categories_and_phase_selection(self):
  import preflight
  self.assertEqual(len(preflight.selected(CHECKS,'core')),8);self.assertEqual(len(preflight.selected(CHECKS,'negatives')),94)
  for exitcode,out,expected in [(4,'assertion might not hold','proof_failure'),(4,'decreases expression might not decrease','termination_failure'),(2,'member does not exist','resolution_failure'),(2,'parse errors','parse_error'),(2,'Warning: trigger','unexpected_diagnostic'),(0,'Warning: trigger','unexpected_warning')]:
   self.assertEqual(preflight.diagnostic(dict(exit_code=exitcode,stdout=out,stderr='')),expected)
 def test_isolated_import_fake_process(self):
  script='''import sys,subprocess
from pathlib import Path
from unittest.mock import patch
root=Path(sys.argv[1]);sys.path.insert(0,str(root));import preflight
checks=preflight.load(root/'checks.json');assert len(checks)==126
sources={p.name:p.read_bytes() for p in (root/checks[0]['path']).glob('*.dfy')}
def fake(command,**kwargs):
 assert command==['timeout','-k','5s','60s','dafny','verify','--verify-included-files','All.dfy']
 assert {p.name:p.read_bytes() for p in Path(kwargs['cwd']).glob('*.dfy')}==sources
 return subprocess.CompletedProcess(command,0,'fake only','')
with patch('subprocess.run',side_effect=fake) as p:
 r=preflight.verify_repository(sources,'All.dfy',60);assert p.call_count==1 and r.evidence['exit_code']==0
'''
  p=subprocess.run([sys.executable,'-I','-B','-c',script,str(ROOT)],capture_output=True,text=True,timeout=20);self.assertEqual(p.returncode,0,p.stdout+p.stderr)
if __name__=='__main__':unittest.main(verbosity=2)
