"""Offline exact edits and guarded source boundaries; no provider/verifier calls."""
import hashlib,json,subprocess,sys,unittest
from pathlib import Path
import body_guard,extract_response
from prepare import transform
ROOT=Path(__file__).resolve().parent
def load(p):return json.loads(p.read_text())
def files(p):return {f.name:f.read_text() for f in p.glob('*.dfy')}
class Tests(unittest.TestCase):
 def test_exact_edits_and_guarded_roundtrip(self):
  for case in load(ROOT/'cases.json'):
   p=ROOT/'parents'/case['variant'];task=load(p/'task.json');seeds=files(p/'seed');raw,_=extract_response.extract_json(load(p/'response.json')['text']);old=json.loads(raw);new=load(p/'analyst-body.json')
   for name,body in old.items():
    changed,count=transform(body,case['variant']);self.assertEqual(new[name],changed);self.assertEqual(count,case['edit_sites_per_body'][name]);self.assertNotEqual(body,changed)
   candidate,decision=extract_response.parse_response((p/'analyst-body.json').read_text(),seeds,task,body_guard)
   # File newline outside JSON does not affect exact JSON span or body insertion.
   self.assertEqual(candidate,files(ROOT/'fixtures'/case['variant']));self.assertEqual(decision['body_guard']['candidate_sha256'],case['candidate_sha256'])
   original=files(p/'candidate')
   for n in seeds:
    if n not in task['editable_files']:self.assertEqual(candidate[n],original[n])
 def test_original_failure_and_edit_specificity(self):
  cases=load(ROOT/'cases.json');self.assertEqual([c['original_outcome'] for c in cases],['PROOF_FAILURE','WARNING_ONLY'])
  for c in cases:
   p=ROOT/'parents'/c['variant'];old=json.loads(extract_response.extract_json(load(p/'response.json')['text'])[0]);new=load(p/'analyst-body.json')
   for n in new:
    if c['variant']=='added_inner_fact':self.assertEqual(new[n].count('if q != j { O2.PutAt(m,k,x,q); }'),2)
    else:
     for call in ['A.ObservePut(', 'A.ObserveDrop(', 'A.Equal(']:self.assertEqual(new[n].count(call),old[n].count(call))
     self.assertEqual(new[n].count('map q |'),old[n].count('map q |')-2)
 def test_isolated_runtime(self):
  script='import sys;sys.path.insert(0,sys.argv[1]);import preflight;assert len(preflight.load(preflight.ROOT/"checks.json"))==2'
  p=subprocess.run([sys.executable,'-I','-B','-c',script,str(ROOT)],capture_output=True,text=True,timeout=15);self.assertEqual(p.returncode,0,p.stdout+p.stderr)
if __name__=='__main__':unittest.main(verbosity=2)
