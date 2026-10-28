"""Fake provider/verifier tests only. Zero SDK requests and zero Dafny processes."""
import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import run_pilot as r
from bounded_requests import RequestGate,GateClosed,bedrock_transport

class Runner(unittest.TestCase):
 def setUp(self):
  self.settings,self.tasks,self.trials=r.validate_bundle();self.prompts=[(r.ROOT/'frozen-001'/t['prompt_path']).read_text() for t in self.trials];self.sent=[];self.checked=[]
 def response(self,index,**changes):
  trial=self.trials[index];task=next(t for t in self.tasks if t['task_id']==trial['task_id']);seed=r.sources(r.ROOT,task)
  resp=dict(text=json.dumps({n:seed[n].decode() for n in task['editable_files']}),request_id='fake-request-%d'%index,retry_attempts=0,usage={'inputTokens':1,'outputTokens':1},stop_reason='end_turn');resp.update(changes);return resp
 def transport(self,messages):
  i=len(self.sent);self.assertEqual(messages,[{'role':'system','content':(r.ROOT/'frozen-001/system.txt').read_text()},{'role':'user','content':self.prompts[i]}]);self.sent.append(copy.deepcopy(messages));return self.response(i)
 def verifier(self,files,code=0):
  self.checked.append(copy.deepcopy(files));return dict(exit_code=code,source_sha256=r.hashes(files),stdout='FAKE verifier output',stderr='',command=['FAKE'],model_calls=0)
 def collect(self,out,transport=None,verifier=None,deadline=100,clock=lambda:0):
  return r.collect(out,transport or self.transport,verifier or self.verifier,deadline,clock=clock,check_runtime=False)
 def test_all32_fixed_order_fresh_prompts_and_hashes(self):
  with tempfile.TemporaryDirectory() as d:
   rows=self.collect(d)
   self.assertEqual(len(self.sent),32);self.assertEqual(len(self.checked),32);self.assertTrue(all(x['outcome']=='VERIFIED' for x in rows))
   ledger=r.load(Path(d)/'requests/ledger.json');self.assertEqual(len(ledger['reservations']),32);self.assertTrue(all(x['status']=='COMPLETED' for x in ledger['reservations']))
   self.assertEqual([x['attempt_id'] for x in ledger['reservations']],[x['trial_id'] for x in self.trials])
   self.assertTrue(r.load(Path(d)/'summary.json')['all_trials_processed'])
 def test_no_retry_after_ambiguous_request(self):
  def fail(messages):self.sent.append(messages);raise TimeoutError('fake timeout')
  with tempfile.TemporaryDirectory() as d:
   rows=self.collect(d,transport=fail);self.assertEqual(len(self.sent),1);self.assertEqual(rows[0]['outcome'],'REQUEST_STOP')
   ledger=r.load(Path(d)/'requests/ledger.json');self.assertTrue(ledger['closed']);self.assertEqual(ledger['reservations'][0]['status'],'AMBIGUOUS_OR_UNSAVED')
 def test_guard_rejections_continue_without_reassignment(self):
  def bad(messages):self.sent.append(messages);return self.response(len(self.sent)-1,text='not JSON')
  with tempfile.TemporaryDirectory() as d:
   rows=self.collect(d,transport=bad);self.assertEqual(len(self.sent),32);self.assertFalse(self.checked);self.assertTrue(all(x['outcome']=='OUTPUT_REJECTED' for x in rows))
 def test_proof_and_frontend_failures_continue(self):
  def fail(files):return self.verifier(files,code=2 if len(self.checked)%2 else 4)
  with tempfile.TemporaryDirectory() as d:
   rows=self.collect(d,verifier=fail);self.assertEqual(len(rows),32);self.assertEqual({x['outcome'] for x in rows},{'PROOF_FAILURE','FRONTEND_ERROR'})
 def test_verifier_timeout_and_hash_mismatch_stop(self):
  for evidence,outcome in [(dict(exit_code=124),'VERIFIER_STOP'),(dict(exit_code=0,source_sha256={}), 'EVIDENCE_MISMATCH')]:
   self.sent=[]
   def stop(files):return dict(source_sha256=r.hashes(files),**evidence) if 'source_sha256' not in evidence else evidence
   with tempfile.TemporaryDirectory() as d:
    rows=self.collect(d,verifier=stop);self.assertEqual(len(self.sent),1);self.assertEqual(rows[0]['outcome'],outcome)
 def test_duplicate_ids_and_retry_metadata_stop(self):
  for mode in ['duplicate','retry']:
   self.sent=[]
   def bad(messages):
    i=len(self.sent);self.sent.append(messages);return self.response(i,request_id='same',retry_attempts=1 if mode=='retry' else 0)
   with tempfile.TemporaryDirectory() as d:
    rows=self.collect(d,transport=bad);self.assertEqual(len(self.sent),2 if mode=='duplicate' else 1);self.assertEqual(rows[-1]['outcome'],'REQUEST_METADATA_STOP')
 def test_deadline_and_existing_ledger(self):
  with tempfile.TemporaryDirectory() as d:
   rows=self.collect(d,deadline=1,clock=lambda:2);self.assertFalse(self.sent);self.assertEqual(rows[0]['outcome'],'REQUEST_STOP')
   with self.assertRaises(FileExistsError):self.collect(d)
 def test_seed_drift_before_second_call_stops(self):
  original=r.validate_bundle;count=[0]
  def changed(root):
   count[0]+=1
   if count[0]==3:raise ValueError('fake drift')
   return original(root)
  with tempfile.TemporaryDirectory() as d,patch.object(r,'validate_bundle',side_effect=changed):
   with self.assertRaises(ValueError):self.collect(d)
   self.assertEqual(len(self.sent),1);self.assertEqual(r.load(Path(d)/'summary.json')['reserved_calls'],1)
 def test_frozen_tamper_blocks_before_transport(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'frozen-001').mkdir();(root/'frozen-001/freeze.json').write_text('{}')
   with self.assertRaises(ValueError):r.collect(root, self.transport,self.verifier,100,root=root,check_runtime=False)
   self.assertFalse(self.sent)
 def test_authorization_binds_budget_pins_and_expiry(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'runtime-freeze.json').write_text('{}')
   a=dict(authorized=True,max_calls=32,automatic_retries=False,reassign_unused=False,proposal_freeze_sha256=r.PROPOSAL_SHA,runtime_freeze_sha256=r.sha(root/'runtime-freeze.json'),expires_at_epoch=100,authorization_basis='fake user test')
   (root/'authorization.json').write_text(json.dumps(a));self.assertEqual(r.validate_authorization(root,0)[1],100)
   for changes in [dict(max_calls=33),dict(automatic_retries=True),dict(reassign_unused=True),dict(expires_at_epoch=0),dict(proposal_freeze_sha256='bad'),dict(runtime_freeze_sha256='bad')]:
    (root/'authorization.json').write_text(json.dumps(dict(a,**changes)))
    with self.assertRaises(ValueError):r.validate_authorization(root,0)
 def test_sdk_no_retry_and_exact_converse_payload(self):
  seen={}
  class Client:
   def converse(self,**kwargs):seen['request']=kwargs;return {'output':{'message':{'content':[{'text':'fake'}]}},'ResponseMetadata':{'RequestId':'fake','RetryAttempts':0}}
  def config(**kwargs):seen['config']=kwargs;return kwargs
  def factory(name,**kwargs):seen['service']=name;return Client()
  messages=[dict(role='system',content='fixed system\n'),dict(role='user',content='fixed prompt\n')]
  result=bedrock_transport(self.settings,client_factory=factory,config_factory=config)(messages)
  self.assertEqual(seen['config']['retries']['total_max_attempts'],1);self.assertEqual(seen['request']['system'],[{'text':'fixed system\n'}]);self.assertEqual(seen['request']['messages'],[{'role':'user','content':[{'text':'fixed prompt\n'}]}]);self.assertEqual(seen['request']['inferenceConfig'],self.settings['inference_config']);self.assertEqual(result['retry_attempts'],0)
 def test_gate_limit_response_write_failure_and_no_reopen(self):
  with tempfile.TemporaryDirectory() as d:
   sent=[];gate=RequestGate(Path(d)/'a',1,100,lambda p:sent.append(p) or {},clock=lambda:0);gate.invoke([],task_id='t',attempt_id='a')
   with self.assertRaises(GateClosed):gate.invoke([],task_id='t',attempt_id='b')
   self.assertEqual(len(sent),1)
   with self.assertRaises(FileExistsError):RequestGate(Path(d)/'a',1,100,lambda p:{},clock=lambda:0)
   gate=RequestGate(Path(d)/'b',2,100,lambda p:object(),clock=lambda:0)
   with self.assertRaises(TypeError):gate.invoke([],task_id='t',attempt_id='a')
   with self.assertRaises(GateClosed):gate.invoke([],task_id='t',attempt_id='b')
if __name__=='__main__':unittest.main()
