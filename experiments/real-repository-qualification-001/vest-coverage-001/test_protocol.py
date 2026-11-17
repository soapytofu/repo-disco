"""Synthetic schema/integrity tests; these do not establish real Vest mathematics."""
import json,unittest
import protocol as g

def report(names,failed=(),entire=True):
 return {'verification-results':{'encountered-error':bool(failed),'encountered-vir-error':False,'is-verifying-entire-crate':entire,'success':not failed and entire,'errors':len(failed),'verified':len(names)-len(failed)},
  'times-ms':{'smt':{'smt-run-module-times':[{'module':'test','function-breakdown':[{'function':n,'success':n not in failed,'mode:':'Proof','time':1,'rlimit':10} for n in names]}]}}}
class Tests(unittest.TestCase):
 def call(self,doc,code=0,required=('Provider::proof','Client::proof'),err=b''):
  raw=json.dumps(doc,indent=2).encode() if doc else b''
  return g.verus_observation(code,raw,err,required)
 def test_full_inventory(self):
  o=self.call(report(['Provider::proof','Client::proof']));self.assertTrue(o['proof_pass']);self.assertTrue(o['strict_zero_warning_pass'])
 def test_success_without_provider_rejected(self):
  o=self.call(report(['Client::proof']));self.assertFalse(o['proof_pass']);self.assertFalse(o['coverage_complete'])
 def test_failed_provider_even_if_client_passes(self):
  o=self.call(report(['Provider::proof','Client::proof'],['Provider::proof']),code=1)
  self.assertEqual(o['category'],'PROOF_FAILURE');self.assertFalse(o['proof_pass']);self.assertTrue(o['units']['Client::proof'])
 def test_filtered_crate_rejected(self):
  self.assertFalse(self.call(report(['Provider::proof','Client::proof'],entire=False))['proof_pass'])
 def test_omitted_function_rejected(self):
  o=self.call(report(['Provider::proof','Client::proof']),required=['Provider::proof','Client::proof','Detached::failure']);self.assertFalse(o['proof_pass'])
 def test_zero_exit_without_report_or_truncated_json_rejected(self):
  self.assertFalse(self.call(None)['proof_pass'])
  self.assertFalse(g.verus_observation(0,b'{"verification-results":',b'',[])['proof_pass'])
 def test_warning_frontend_environment_timeout_separate(self):
  o=self.call(report(['Provider::proof','Client::proof']),err=b'warning: example\n');self.assertEqual(o['category'],'PROVED_WITH_WARNINGS');self.assertFalse(o['strict_zero_warning_pass'])
  self.assertEqual(self.call(None,code=101,err=b'error: linker `cc` not found')['category'],'ENVIRONMENT_OR_BUILD_ERROR')
  self.assertEqual(self.call(None,code=101,err=b'error[E0308]: mismatched types')['category'],'RUST_FRONTEND_FAILURE')
  self.assertEqual(self.call(report(['Provider::proof','Client::proof']),code=124)['category'],'TIMEOUT_OR_KILLED')
 def test_two_native_reports_merge_and_duplicate_rejected(self):
  raw=(json.dumps(report(['Provider::proof']),indent=2)+'\n'+json.dumps(report(['Client::proof']),indent=2)).encode()
  self.assertTrue(g.verus_observation(0,raw,b'',['Provider::proof','Client::proof'])['proof_pass'])
  with self.assertRaises(ValueError):g.verus_observation(0,raw+b'\n'+json.dumps(report(['Client::proof'])).encode(),b'')
if __name__=='__main__':unittest.main(verbosity=2)
