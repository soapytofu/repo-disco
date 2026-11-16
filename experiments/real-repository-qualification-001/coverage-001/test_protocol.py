import copy,csv,io,json,unittest
from pathlib import Path
import protocol as g
R=Path(__file__).resolve().parent
class ProtocolTests(unittest.TestCase):
 def setUp(self):
  self.profile=json.loads((R/'profile.json').read_bytes())
  raw=R/'native-fixture'
  self.stdout=(raw/'stdout.txt').read_bytes();self.stderr=(raw/'stderr.txt').read_bytes()
  self.csv={'baseline.csv':(raw/'baseline.csv').read_bytes()}
 def observation(self,csv=None,required=None):
  return g.dafny_observation(0,self.stdout,self.stderr,self.csv if csv is None else csv,self.profile['required_units'] if required is None else required)
 def test_actual_baseline_warning_classification(self):
  o=self.observation();self.assertEqual(o['category'],'PROVED_WITH_WARNINGS');self.assertTrue(o['proof_pass']);self.assertFalse(o['strict_zero_warning_pass']);self.assertEqual(len(o['units']),267)
 def test_missing_failure_file_rejected(self):
  required={**self.profile['required_units'],'QualificationDetached.Fails (correctness)':'tests/QualificationDetached.dfy'}
  o=self.observation(required=required);self.assertFalse(o['coverage_complete']);self.assertFalse(o['proof_pass'])
 def test_missing_helper_or_corrupt_csv_not_accepted(self):
  rows=list(csv.reader(io.StringIO(self.csv['baseline.csv'].decode())))
  stripped=[r for r in rows if not r[0].endswith('.Swap (correctness)')]
  b=io.StringIO(newline='');csv.writer(b).writerows(stripped)
  self.assertFalse(self.observation({'baseline.csv':b.getvalue().encode()})['proof_pass'])
  with self.assertRaises(ValueError):self.observation({'baseline.csv':b'wrong,header\n'})
 def test_failed_helper_cannot_be_summary_success(self):
  raw=self.csv['baseline.csv'].replace(b'Trait.Swap (correctness),Passed',b'Trait.Swap (correctness),Failed')
  self.assertNotEqual(raw,self.csv['baseline.csv']);self.assertFalse(self.observation({'baseline.csv':raw})['proof_pass'])
 def test_frontend_and_timeouts_distinct(self):
  self.assertEqual(g.dafny_observation(2,b'1 parse errors detected',b'',{})['category'],'PARSE_FAILURE')
  self.assertEqual(g.dafny_observation(124,self.stdout,self.stderr,self.csv)['category'],'TIMEOUT_OR_KILLED')
 def test_contract_bypass_addition_and_missing_file_rejected(self):
  base=self.profile['source_sha256']
  for bad in [{**base,'new.dfy':'0'*64},{**base,'dfyconfig.toml':'0'*64},{k:v for k,v in base.items() if k!='src/Util/FisherYates/Implementation.dfy'}]:
   with self.assertRaises(ValueError):g.check_sources(bad,base)
 def test_stale_and_missing_evidence_rejected(self):
  raw={'stdout.txt':self.stdout,'stderr.txt':self.stderr,**self.csv};p={**self.profile,'logical_command':['verify','known-scope']}
  record=dict(run_id='review:1',profile_sha256=g.sha(g.canonical(p)),source_sha256=p['source_sha256'],source_after_sha256=p['source_sha256'],logical_command=p['logical_command'],toolchain=p['toolchain'],raw_sha256={n:g.sha(b) for n,b in sorted(raw.items())},model_calls=0,attempts=1,exit_code=0,elapsed_seconds=1)
  g.check_record(record,p,'review:1',raw)
  for key,value in [('run_id','old'),('profile_sha256','0'*64),('raw_sha256',{}),('source_after_sha256',{}),('logical_command',['verify','client-only']),('toolchain',{}),('elapsed_seconds',float('inf')),('exit_code',None)]:
   with self.subTest(key=key),self.assertRaises(ValueError):g.check_record({**record,key:value},p,'review:1',raw)
 def test_coverage_file_accounting_and_exact_patch(self):
  p=self.profile;self.assertEqual(set(p['required_units'].values())|set(p['unlogged_files']),set(p['explicit_sources']))
  patches=json.loads((R/'patches.json').read_bytes());n='src/Util/FisherYates/Implementation.dfy'
  raw=(R/'patches/vmc_broken_swap'/n).read_bytes();self.assertEqual(g.sha(raw),patches['vmc_broken_swap'][n])
  restored=raw.replace(b'a[i], a[j] := a[i], a[j];',b'a[i], a[j] := a[j], a[i];')
  self.assertEqual(g.sha(restored),p['source_sha256'][n])
if __name__=='__main__':unittest.main(verbosity=2)
