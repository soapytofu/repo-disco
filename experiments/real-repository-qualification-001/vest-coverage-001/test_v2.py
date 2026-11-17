"""Actual native evidence replay and hostile coverage/integrity controls; no verifier."""
import copy,json,tempfile,unittest
from pathlib import Path
import protocol_v2 as g
ROOT=Path(__file__).resolve().parent

def document(names=('vest_lib::Provider::proof','vest_lib::Client::proof'),failed=(),crate='vest_lib'):
 return {'verus':{'version':'synthetic'},'verification-results':{'encountered-error':bool(failed),'encountered-vir-error':False,'is-verifying-entire-crate':True,'success':not failed,'errors':len(failed),'verified':len(names)-len(failed)},'times-ms':{'num-threads':3,'smt':{'smt-run-module-times':[{'module':'test','function-breakdown':[{'function':n,'success':n not in failed,'mode:':'proof'} for n in names]}]}}}
def observe(doc,code=0,required=None,stderr=b''):return g.verus_observation(code,json.dumps(doc,indent=2).encode(),stderr,required)
def req(o):return dict(inventory=o['inventory'],crates=list(o['crates']),version={'version':'synthetic'},num_threads=3)
class Tests(unittest.TestCase):
 def test_actual_native_replay(self):
  for package in ('vest_lib','vest_dev'):
   d=ROOT.parent/'vest-container-004/results'/('native-'+package);r=json.loads((d/'record.json').read_bytes())
   o=g.verus_observation(r['exit_code'],(d/'stdout.txt').read_bytes(),(d/'stderr.txt').read_bytes())
   self.assertEqual(o,json.loads((ROOT/('native-'+package+'-observation.json')).read_bytes()))
   self.assertTrue(o['proof_pass']);self.assertEqual(len(o['warnings']),5 if package=='vest_dev' else 0)
  base=json.loads((ROOT/'profile.json').read_bytes());d=ROOT.parent/'vest-container-004/results/native-vest_dev'
  self.assertTrue(g.verus_observation(0,(d/'stdout.txt').read_bytes(),(d/'stderr.txt').read_bytes(),base['required'])['coverage_complete'])
 def test_preserved_build_errors_not_proof_failure(self):
  for pkg in ('vest_lib','vest_dev'):
   d=ROOT.parent/'vest-container-002/results'/('native-'+pkg);r=json.loads((d/'record.json').read_bytes())
   self.assertEqual(g.verus_observation(r['exit_code'],(d/'stdout.txt').read_bytes(),(d/'stderr.txt').read_bytes())['category'],'ENVIRONMENT_OR_BUILD_ERROR')
 def test_repeat_labels_require_exact_multiplicity(self):
  doc=document(('vest_lib::same','vest_lib::same'));baseline=observe(doc)
  self.assertEqual(sum(baseline['inventory'].values()),2);self.assertEqual(len(baseline['units']),1)
  self.assertTrue(observe(doc,required=req(baseline))['proof_pass'])
  doc['times-ms']['smt']['smt-run-module-times'][0]['function-breakdown'].pop()
  self.assertFalse(observe(doc,required=req(baseline))['proof_pass'])
 def test_duplicate_failure_cannot_be_overwritten(self):
  doc=document(('vest_lib::same','vest_lib::same'));doc['times-ms']['smt']['smt-run-module-times'][0]['function-breakdown'][0]['success']=False
  self.assertFalse(observe(doc)['proof_pass'])
 def test_duplicate_reports_rejected(self):
  raw=json.dumps(document()).encode()
  with self.assertRaises(ValueError):g.verus_observation(0,raw+b'\n'+raw,b'')
 def test_missing_helper_and_omitted_file_rejected(self):
  baseline=observe(document());r=req(baseline)
  self.assertFalse(observe(document(('vest_lib::Client::proof',)),required=r)['proof_pass'])
  r['inventory'][json.dumps(['vest_lib','test','vest_lib::detached','proof'],separators=(',',':'))]=1
  self.assertFalse(observe(document(),required=r)['proof_pass'])
 def test_failed_helper_with_passing_client_rejected(self):
  o=observe(document(failed=['vest_lib::Provider::proof']),1)
  self.assertFalse(o['proof_pass']);self.assertEqual(o['category'],'PROOF_FAILURE');self.assertTrue(o['units']['vest_lib::Client::proof'])
 def test_warning_frontend_timeout_and_no_output(self):
  self.assertEqual(observe(document(),stderr=b'warning: x\n  --> a.rs:1:1\n\n')['category'],'PROVED_WITH_WARNINGS')
  self.assertEqual(observe(document(),101,stderr=b'error[E0308]: x')['category'],'RUST_FRONTEND_FAILURE')
  self.assertEqual(observe(document(),124)['category'],'TIMEOUT_OR_KILLED')
  self.assertFalse(g.verus_observation(0,b'',b'')['proof_pass'])
  with self.assertRaises(ValueError):g.verus_observation(0,json.dumps(document()).encode()+b'\n{"verification-results":',b'')
 def test_version_thread_filtered_errors_rejected(self):
  doc=document();r=req(observe(doc));r['version']={'version':'other'};self.assertFalse(observe(doc,required=r)['proof_pass'])
  r=req(observe(doc));r['num_threads']=4;self.assertFalse(observe(doc,required=r)['proof_pass'])
  doc['verification-results']['is-verifying-entire-crate']=False;self.assertFalse(observe(doc)['proof_pass'])
 def test_integrity_sources_command_evidence_and_run_id(self):
  profile=dict(source_sha256={'src/a.rs':'original'},logical_command=['verify'],toolchain={'version':'pinned'});raw={'stdout.txt':b'native'}
  record=dict(run_id='job:trial',profile_sha256=g.sha(g.canonical(profile)),source_sha256=profile['source_sha256'],source_after_sha256=profile['source_sha256'],logical_command=profile['logical_command'],toolchain=profile['toolchain'],raw_sha256={n:g.sha(b) for n,b in raw.items()},model_calls=0,attempts=1,exit_code=0,elapsed_seconds=1)
  g.check_record(record,profile,'job:trial',raw)
  for key,value in [('run_id','old:trial'),('source_sha256',{'src/a.rs':'changed contract'}),('source_after_sha256',{}),('logical_command',['focus']),('toolchain',{}),('raw_sha256',{}),('elapsed_seconds',float('nan')),('attempts',2)]:
   with self.subTest(key=key),self.assertRaises(ValueError):g.check_record({**record,key:value},profile,'job:trial',raw)
 def test_exact_host_patch_preserves_original_header(self):
  patches=json.loads((ROOT/'patches.json').read_bytes());source=ROOT.parent/'upstream/vest'
  before=(source/'vest_lib/src/core/proof.rs').read_text();after=(ROOT/'patches/vest_broken_provider/vest_lib/src/core/proof.rs').read_text()
  self.assertEqual(after.replace('        assert(false); // deliberate qualification control\n',''),before)
  for case,files in patches.items():
   for n,h in files.items():self.assertEqual(g.sha((ROOT/'patches'/case/n).read_bytes()),h)
  self.assertEqual((ROOT/'patches/vest_registered/vest_dev/src/lib.rs').read_text().removesuffix('\npub mod qualification_detached;\n'),(source/'vest_dev/src/lib.rs').read_text())
if __name__=='__main__':unittest.main(verbosity=2)
