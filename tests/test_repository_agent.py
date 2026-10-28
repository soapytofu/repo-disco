import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from language import VerificationOutput,VerificationOutcome
from language.dafny.candidate import prepare_candidate,hashes
from repository_agent import RevisionStore,repair as actual_repair

def repair(*args,**kwargs):
    kwargs.setdefault("base_verifier",lambda files,entry:SimpleNamespace(verification=VerificationOutput(VerificationOutcome.FAIL,4,"initial error",""),evidence={"exit_code":4,"source_sha256":hashes(files)}))
    return actual_repair(*args,**kwargs)

class Gate:
    def __init__(self,responses):self.responses=iter(responses);self.prompts=[]
    def invoke(self,prompt,**kwargs):self.prompts.append(prompt);return next(self.responses)

def decode(raw,base):return {k:v.encode() for k,v in raw.items()}
def result(candidate,code):
    return SimpleNamespace(verification=VerificationOutput(VerificationOutcome.SUCCESS if code==0 else VerificationOutcome.FAIL,code,'feedback',''),evidence=dict(exit_code=code,source_sha256=hashes(candidate.files)))

class AgentTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.files={'A.dfy':b'contract:broken','B.dfy':b'client'}
        self.manifest=dict(task_id='test',entry='B.dfy',editable=['A.dfy'],dependencies={'A.dfy':[],'B.dfy':['A.dfy']})
        self.store=RevisionStore.create(Path(self.temp.name)/'store',self.files,self.manifest)
        def guard(before,after):
            if not after.startswith(b'contract:'):raise ValueError('contract changed')
        self.guards={'A.dfy':guard}
    def test_failure_feedback_then_atomic_success(self):
        gate=Gate([{'A.dfy':'contract:wrong'},{'A.dfy':'contract:correct'}]);base=self.store.snapshot()
        def verify(candidate):
            self.assertEqual(self.store.snapshot().revision,base.revision)
            return result(candidate,0 if candidate.files['A.dfy'].endswith(b'correct') else 4)
        records=repair(self.store,gate,decode,self.guards,attempt_limit=2,verifier=verify)
        self.assertEqual([r['outcome'] for r in records],['PROOF_FAILURE','SUCCESS'])
        self.assertEqual(gate.prompts[1]['feedback']['stdout'],'feedback')
        self.assertEqual(gate.prompts[1]['files']['A.dfy'],'contract:broken')
        self.assertEqual(self.store.snapshot().files['B.dfy'],b'client')
        self.assertNotEqual(self.store.snapshot().revision,base.revision)
    def test_guard_rejection_never_verifies(self):
        base=self.store.snapshot()
        with patch('repository_agent.verify_candidate') as verify:
            records=repair(self.store,Gate([{'A.dfy':'changed'}]),decode,self.guards,attempt_limit=1,verifier=verify)
        verify.assert_not_called();self.assertEqual(records[0]['outcome'],'EDIT_REJECTED')
        self.assertEqual(self.store.snapshot().revision,base.revision)
    def test_failed_verification_and_timeout_do_not_promote(self):
        for code in [4,124]:
            base=self.store.snapshot();gate=Gate([{'A.dfy':'contract:x'}])
            records=repair(self.store,gate,decode,self.guards,attempt_limit=1,verifier=lambda c:result(c,code))
            self.assertEqual(self.store.snapshot().revision,base.revision)
    def test_stale_promotion_rejected(self):
        base=self.store.snapshot();c=prepare_candidate(base.files,{'A.dfy':b'contract:x'},entry='B.dfy',expected_hashes=hashes(base.files),guards=self.guards)
        self.store.promote(base,c,result(c,0))
        with self.assertRaisesRegex(ValueError,'stale'):self.store.promote(base,c,result(c,0))
    def test_pointer_write_failure_preserves_whole_old_revision(self):
        base=self.store.snapshot();c=prepare_candidate(base.files,{'A.dfy':b'contract:x'},entry='B.dfy',expected_hashes=hashes(base.files),guards=self.guards)
        import repository_agent
        original=repository_agent.atomic_json
        def fail_head(path,value):
            if path.name=='HEAD.json':raise OSError('simulated crash')
            return original(path,value)
        with patch('repository_agent.atomic_json',side_effect=fail_head):
            with self.assertRaises(OSError):self.store.promote(base,c,result(c,0))
        self.assertEqual(self.store.snapshot().files,base.files)
        self.assertEqual(self.store.snapshot().revision,base.revision)
    def test_already_verified_uses_no_request(self):
        gate=Gate([])
        base_verify=lambda files,entry:SimpleNamespace(verification=VerificationOutput(VerificationOutcome.SUCCESS,0,'',''),evidence={'exit_code':0})
        records=repair(self.store,gate,decode,self.guards,attempt_limit=2,base_verifier=base_verify)
        self.assertEqual(records[0]['outcome'],'ALREADY_VERIFIED');self.assertEqual(gate.prompts,[])

    def test_source_tampering_detected(self):
        base=self.store.snapshot();(self.store.path/'revisions'/base.revision/'files/A.dfy').write_bytes(b'tampered')
        with self.assertRaises(ValueError):self.store.snapshot()
    def test_budget_exception_stops_without_verifier(self):
        class Closed:
            def invoke(self,*args,**kwargs):raise RuntimeError('closed')
        with patch('repository_agent.verify_candidate') as verify:
            records=repair(self.store,Closed(),decode,self.guards,attempt_limit=3,verifier=verify)
        self.assertEqual(len(records),1);self.assertEqual(records[0]['outcome'],'REQUEST_STOP');verify.assert_not_called()
    def test_mismatched_verification_hash_cannot_promote(self):
        base=self.store.snapshot();c=prepare_candidate(base.files,{'A.dfy':b'contract:x'},entry='B.dfy',expected_hashes=hashes(base.files),guards=self.guards)
        verified=result(c,0);verified.evidence['source_sha256']={}
        with self.assertRaises(ValueError):self.store.promote(base,c,verified)

if __name__=='__main__':unittest.main()
