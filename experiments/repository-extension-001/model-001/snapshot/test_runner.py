"""Fake transport and fake verifier only; no cluster, SDK or network access."""
import json,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
import run_pilot as runner
from extension import ROOT,hashes

class RunnerTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.out=Path(self.temp.name)
  self.settings,self.tasks,self.prompts=runner.validate_bundle();self.calls=[];self.verified=[]
 def response(self,messages):
  self.calls.append(messages);task=json.loads(messages[1]['content'])['task_id']
  raw=(ROOT/'controls'/task/'reference.json').read_text()
  return dict(text=raw,request_id='fake-'+str(len(self.calls)),retry_attempts=0,usage={'totalTokens':1})
 def verify(self,files):
  self.verified.append(dict(files));return dict(exit_code=0,source_sha256=hashes(files),stdout='0 errors',stderr='')
 def test_exact_four_order_prompts_and_acceptance(self):
  before={f:f.read_bytes() for f in (ROOT/'seeds').rglob('*.dfy')}
  rows=runner.collect(self.out,self.response,self.verify,time.time()+60)
  self.assertEqual([r['outcome'] for r in rows],['VERIFIED_EXTENSION']*4)
  self.assertEqual(self.calls,[p['messages'] for p in self.prompts]);self.assertEqual(len(self.verified),4)
  self.assertEqual({f:f.read_bytes() for f in before},before)
  self.assertEqual(json.loads((self.out/'summary.json').read_text())['reserved_calls'],4)
  for i in range(1,5):self.assertTrue((self.out/f'{i:02d}/accepted.json').exists())
  with self.assertRaises(FileExistsError):runner.collect(self.out,self.response,self.verify,time.time()+60)
  self.assertEqual(len(self.calls),4)
 def test_guard_and_proof_failures_are_completed_trials(self):
  def transport(messages):
   r=self.response(messages)
   if len(self.calls)==1:r['text']='{"Facts.dfy":"bypass"}'
   return r
  def verifier(files):
   r=self.verify(files)
   if len(self.verified)==1:r.update(exit_code=4,stdout='postcondition could not be proved')
   return r
  rows=runner.collect(self.out,transport,verifier,time.time()+60)
  self.assertEqual([r['outcome'] for r in rows],['EDIT_REJECTED','PROOF_FAILURE','VERIFIED_EXTENSION','VERIFIED_EXTENSION'])
  self.assertFalse((self.out/'01/verification.json').exists());self.assertFalse((self.out/'02/accepted.json').exists())
 def test_ambiguous_transport_never_retried(self):
  def transport(messages):self.calls.append(messages);raise TimeoutError('fake')
  rows=runner.collect(self.out,transport,self.verify,time.time()+60)
  self.assertEqual(len(self.calls),1);self.assertEqual(rows[0]['outcome'],'REQUEST_STOP');self.assertEqual(self.verified,[])
  d=json.loads((self.out/'requests/ledger.json').read_text());self.assertTrue(d['closed']);self.assertEqual(d['reservations'][0]['status'],'AMBIGUOUS_OR_UNSAVED')
 def test_verifier_timeout_and_mismatched_hash_stop(self):
  for kind in ['timeout','mismatch','exception']:
   with self.subTest(kind=kind),tempfile.TemporaryDirectory() as d:
    self.calls=[]
    def verifier(files):
     if kind=='exception':raise OSError('fake')
     return dict(exit_code=124 if kind=='timeout' else 0,source_sha256={} if kind=='mismatch' else hashes(files))
    rows=runner.collect(Path(d),self.response,verifier,time.time()+60)
    self.assertEqual(len(self.calls),1);self.assertTrue(rows[0]['stop']);self.assertFalse((Path(d)/'01/accepted.json').exists())
 def test_deadline_reserves_no_request(self):
  rows=runner.collect(self.out,self.response,self.verify,0)
  self.assertEqual(self.calls,[]);self.assertEqual(rows[0]['outcome'],'REQUEST_STOP')
  self.assertEqual(json.loads((self.out/'summary.json').read_text())['reserved_calls'],0)
 def test_changed_freeze_blocks_next_dispatch(self):
  checks=[]
  def check():
   checks.append(1)
   if len(checks)==3:raise ValueError('fake changed freeze')
   return runner.validate_execution()
  with self.assertRaises(ValueError):runner.collect(self.out,self.response,self.verify,time.time()+60,check=check)
  self.assertEqual(len(self.calls),1);self.assertEqual(json.loads((self.out/'summary.json').read_text())['reserved_calls'],1)
 def test_invalid_response_stops(self):
  def transport(messages):self.calls.append(messages);return {'text':None}
  rows=runner.collect(self.out,transport,self.verify,time.time()+60)
  self.assertEqual(len(self.calls),1);self.assertEqual(rows[0]['outcome'],'RESPONSE_ERROR');self.assertEqual(self.verified,[])
 def test_authorization_required_and_hash_bound(self):
  now=time.time();auth=dict(authorized=True,max_calls=4,automatic_retries=False,reassign_unused=False,authorization_basis='OFFLINE FAKE TEST ONLY',expires_at_epoch=now+60,proposal_freeze_sha256=runner.sha(ROOT/'frozen-001/freeze.json'),runtime_freeze_sha256=runner.sha(ROOT/'runtime-freeze.json'))
  self.assertEqual(runner.validate_authorization(auth,now),now+60)
  for k,v in [('authorized',False),('max_calls',5),('expires_at_epoch',now-1),('runtime_freeze_sha256','wrong'),('proposal_freeze_sha256','wrong'),('authorization_basis','')]:
   with self.subTest(k=k),self.assertRaises(ValueError):runner.validate_authorization({**auth,k:v},now)
 def test_cli_checks_auth_before_credentials_or_transport(self):
  def fake_load(p):
   if p.name=='authorization.json':return {'authorized':False}
   return json.loads(p.read_text())
  with patch.object(runner.sys,'argv',['run_pilot.py','run']),patch.dict(runner.os.environ,{'SLURM_JOB_ID':'fake'}),patch.object(runner.socket,'gethostname',return_value='compute-fake'),patch.object(runner,'load',side_effect=fake_load),patch.object(runner,'consume_key') as key,patch.object(runner,'bedrock_transport') as transport:
   with self.assertRaises(ValueError):runner.main()
   key.assert_not_called();transport.assert_not_called()
 def test_transport_no_retry_configuration(self):
  from bounded_requests import bedrock_transport
  recorded={}
  class Client:
   def converse(self,**kwargs):
    recorded['wire']=kwargs
    return {'output':{'message':{'content':[{'text':'fake'}]}},'usage':{},'stopReason':'end_turn','ResponseMetadata':{'RequestId':'offline','RetryAttempts':0}}
  def factory(service,**kw):recorded.update(service=service,**kw);return Client()
  transport=bedrock_transport(self.settings,client_factory=factory,config_factory=lambda **kw:kw)
  transport(self.prompts[0]['messages'])
  self.assertEqual(recorded['config']['retries']['total_max_attempts'],1)
  self.assertEqual(recorded['wire']['inferenceConfig'],self.settings['inference_config'])
if __name__=='__main__':unittest.main()
