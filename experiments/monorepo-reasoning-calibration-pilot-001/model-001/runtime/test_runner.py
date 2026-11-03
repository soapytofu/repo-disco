"""Fake provider/verifier tests only. Zero SDK requests and zero Dafny processes."""
import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import run_pilot as r
from bounded_requests import RequestGate,GateClosed,bedrock_transport

class Runner(unittest.TestCase):
 def setUp(self):
  self.settings,self.tasks,self.trials=r.validate_bundle();self.requests=[r.load(r.ROOT/'frozen-001'/t['request_path']) for t in self.trials];self.sent=[];self.checked=[]
 def response(self,index,**changes):
  trial=self.trials[index];task=next(t for t in self.tasks if t['task_id']==trial['task_id']);seed=r.sources(r.ROOT,task)
  resp=dict(text=json.dumps({n:'\n' for n in task['editable_files']}),request_id='fake-request-%d'%index,retry_attempts=0,usage={'inputTokens':1,'outputTokens':1},stop_reason='end_turn');resp.update(changes);return resp
 def transport(self,messages):
  i=len(self.sent);self.assertEqual(messages,self.requests[i]);self.sent.append(copy.deepcopy(messages));return self.response(i)
 def verifier(self,files,code=0):
  self.checked.append(copy.deepcopy(files));return dict(exit_code=code,source_sha256=r.hashes(files),stdout='FAKE verifier output',stderr='',command=['FAKE'],model_calls=0)
 def collect(self,out,transport=None,verifier=None,deadline=100,clock=lambda:0):
  return r.collect(out,transport or self.transport,verifier or self.verifier,deadline,clock=clock,check_runtime=False)
 def test_all24_fixed_order_fresh_prompts_and_hashes(self):
  with tempfile.TemporaryDirectory() as d:
   rows=self.collect(d)
   self.assertEqual(len(self.sent),24);self.assertEqual(len(self.checked),24);self.assertTrue(all(x['outcome']=='VERIFIED' for x in rows))
   ledger=r.load(Path(d)/'requests/ledger.json');self.assertEqual(len(ledger['reservations']),24);self.assertTrue(all(x['status']=='COMPLETED' for x in ledger['reservations']))
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
   rows=self.collect(d,transport=bad);self.assertEqual(len(self.sent),24);self.assertFalse(self.checked);self.assertTrue(all(x['outcome']=='OUTPUT_REJECTED' for x in rows))
 def test_proof_and_frontend_failures_continue(self):
  def fail(files):return self.verifier(files,code=2 if len(self.checked)%2 else 4)
  with tempfile.TemporaryDirectory() as d:
   rows=self.collect(d,verifier=fail);self.assertEqual(len(rows),24);self.assertEqual({x['outcome'] for x in rows},{'PROOF_FAILURE','FRONTEND_ERROR'})
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
   a=dict(authorized=True,max_calls=24,automatic_retries=False,reassign_unused=False,proposal_freeze_sha256=r.PROPOSAL_SHA,runtime_freeze_sha256=r.sha(root/'runtime-freeze.json'),expires_at_epoch=100,authorization_basis='fake user test')
   (root/'authorization.json').write_text(json.dumps(a));self.assertEqual(r.validate_authorization(root,0)[1],100)
   for changes in [dict(max_calls=25),dict(automatic_retries=True),dict(reassign_unused=True),dict(expires_at_epoch=0),dict(proposal_freeze_sha256='bad'),dict(runtime_freeze_sha256='bad')]:
    (root/'authorization.json').write_text(json.dumps(dict(a,**changes)))
    with self.assertRaises(ValueError):r.validate_authorization(root,0)
 def test_sdk_no_retry_and_exact_converse_payload(self):
  seen={};raw={'output':{'message':{'content':[{'text':'fake'}]}},'ResponseMetadata':{'RequestId':'fake','RetryAttempts':0},'stopReason':'end_turn','usage':{'inputTokens':1,'outputTokens':1}}
  class Client:
   def converse(self,**kwargs):seen['request']=kwargs;return raw
  def config(**kwargs):seen['config']=kwargs;return kwargs
  def factory(name,**kwargs):seen['service']=name;return Client()
  payload=self.requests[0]
  result=bedrock_transport(self.settings,client_factory=factory,config_factory=config)(payload)
  self.assertEqual(seen['config']['retries']['total_max_attempts'],1)
  self.assertEqual(seen['request'],payload)
  self.assertEqual(result['retry_attempts'],0);self.assertEqual(result['raw_response'],raw)
 def test_gate_limit_response_write_failure_and_no_reopen(self):
  with tempfile.TemporaryDirectory() as d:
   sent=[];gate=RequestGate(Path(d)/'a',1,100,lambda p:sent.append(p) or {},clock=lambda:0);gate.invoke([],task_id='t',attempt_id='a')
   with self.assertRaises(GateClosed):gate.invoke([],task_id='t',attempt_id='b')
   self.assertEqual(len(sent),1)
   with self.assertRaises(FileExistsError):RequestGate(Path(d)/'a',1,100,lambda p:{},clock=lambda:0)
   gate=RequestGate(Path(d)/'b',2,100,lambda p:object(),clock=lambda:0)
   with self.assertRaises(TypeError):gate.invoke([],task_id='t',attempt_id='a')
   with self.assertRaises(GateClosed):gate.invoke([],task_id='t',attempt_id='b')
 def test_body_assembly_preserves_contracts_and_rejects_full_files(self):
  guard=r.guard_module(r.ROOT)
  for task in self.tasks:
   seed=r.sources(r.ROOT,task)
   with tempfile.TemporaryDirectory() as d:
    result=r.evaluate(task,seed,dict(text=json.dumps({n:'assert true;' for n in task['editable_files']})),Path(d),self.verifier,guard)
    self.assertEqual(result['outcome'],'VERIFIED') # Fake verifier; syntax/bytes only.
    candidate=self.checked[-1]
    for n,b in seed.items():
     if n not in task['editable_files']:self.assertEqual(candidate[n],b)
     else:
      pre,suf=guard.split_seed(b.decode());self.assertEqual(candidate[n],(pre+'assert true;'+suf).encode())
   for bad in [json.dumps({n:seed[n].decode() for n in task['editable_files']}),json.dumps({n:'assume false;' for n in task['editable_files']})]:
    before=len(self.checked)
    with tempfile.TemporaryDirectory() as d:
     result=r.evaluate(task,seed,dict(text=bad),Path(d),self.verifier,guard)
     self.assertEqual(result['outcome'],'OUTPUT_REJECTED');self.assertEqual(len(self.checked),before)
 def test_guard_loads_only_exact_pinned_body_module(self):
  guard=r.guard_module(r.ROOT)
  self.assertEqual(guard.VERSION,self.settings['parser_version'])
  self.assertEqual(r.sha(r.ROOT/'frozen-001/guard/body_guard.py'),self.settings['parser_sha256'])
  for task in self.tasks:
   seed=r.sources(r.ROOT,task)
   result,_=guard.parse_response(json.dumps({n:'\n' for n in task['editable_files']}),{n:b.decode() for n,b in seed.items()},task)
   self.assertEqual({n:s.encode() for n,s in result.items()},seed)
 def test_deadline_after_reservation_never_dispatches(self):
  with tempfile.TemporaryDirectory() as d:
   ticks=iter([0,0,2]);sent=[]
   gate=RequestGate(Path(d)/'requests',24,1,lambda p:sent.append(p),clock=lambda:next(ticks))
   with self.assertRaises(GateClosed):gate.invoke([],task_id='t',attempt_id='a')
   self.assertFalse(sent);self.assertEqual(len(gate.state['reservations']),1)
   self.assertTrue(gate.closed);self.assertEqual(gate.state['closed_reason'],'deadline_before_transport')
 def test_reservation_persistence_failure_blocks_transport(self):
  with tempfile.TemporaryDirectory() as d:
   sent=[];gate=RequestGate(Path(d)/'requests',24,100,lambda p:sent.append(p),clock=lambda:0)
   with patch('bounded_requests.durable_json',side_effect=OSError('fake disk failure')):
    with self.assertRaises(OSError):gate.invoke([],task_id='t',attempt_id='a')
   self.assertFalse(sent);self.assertTrue(gate.closed)
   with self.assertRaises(GateClosed):gate.invoke([],task_id='t',attempt_id='b')
 def test_runtime_drift_before_second_request_stops(self):
  checked=[0]
  def runtime(root):
   checked[0]+=1
   if checked[0]==3:raise ValueError('fake runtime drift')
  with tempfile.TemporaryDirectory() as d,patch.object(r,'validate_runtime',side_effect=runtime):
   with self.assertRaises(ValueError):r.collect(d,self.transport,self.verifier,100,clock=lambda:0)
   self.assertEqual(len(self.sent),1)
   self.assertEqual(r.load(Path(d)/'summary.json')['reserved_calls'],1)

 def test_truncation_consumes_slot_without_verification_or_retry(self):
  def truncated(payload):
   i=len(self.sent);self.sent.append(payload);return self.response(i,stop_reason='max_tokens')
  with tempfile.TemporaryDirectory() as d:
   rows=self.collect(d,transport=truncated)
   self.assertEqual(len(rows),24);self.assertFalse(self.checked)
   self.assertTrue(all(x['outcome']=='OUTPUT_TRUNCATED' for x in rows))
 def test_deadline_after_dispatch_reservation_stops_before_transport(self):
  with tempfile.TemporaryDirectory() as d:
   ticks=iter([0,0,0,0,2]);sent=[]
   gate=RequestGate(Path(d)/'requests',24,1,lambda p:sent.append(p),clock=lambda:next(ticks))
   with self.assertRaises(GateClosed):gate.invoke({},task_id='t',attempt_id='a')
   self.assertFalse(sent)
   self.assertNotIn('dispatch_started_at_epoch',gate.state['reservations'][0])
 def test_closed_gate_after_response_persistence_error_cannot_retry(self):
  import bounded_requests as b
  original=b.durable_json
  def fail_response(path,value):
   if path.name.startswith('response-'):raise OSError('fake response persistence failure')
   return original(path,value)
  with tempfile.TemporaryDirectory() as d:
   sent=[];gate=RequestGate(Path(d)/'requests',24,100,lambda payload:sent.append(payload) or {},clock=lambda:0)
   with patch.object(b,'durable_json',side_effect=fail_response):
    with self.assertRaises(OSError):gate.invoke({},task_id='t',attempt_id='a')
   self.assertTrue(gate.closed);self.assertEqual(len(sent),1)
   with self.assertRaises(GateClosed):gate.invoke({},task_id='t',attempt_id='b')

 def test_saved_evidence_review_roundtrip_and_tamper(self):
  import shutil
  from review_results import review
  from bounded_requests import durable_json
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);shutil.copytree(r.ROOT/'frozen-001',root/'frozen-001')
   for name in r.RUNTIME_FILES:shutil.copy2(r.ROOT/name,root/name)
   pins=dict(proposal_freeze_sha256=r.PROPOSAL_SHA,max_calls=24,automatic_retries=False,reassign_unused=False,
    runtime_sha256={n:r.sha(root/n) for n in sorted(r.RUNTIME_FILES)})
   durable_json(root/'runtime-freeze.json',pins)
   out=root/'model-001';out.mkdir()
   shutil.copytree(root/'frozen-001',out/'frozen-001');shutil.copy2(root/'runtime-freeze.json',out/'runtime-freeze.json')
   (out/'runtime').mkdir()
   for name in r.RUNTIME_FILES:shutil.copy2(root/name,out/'runtime'/name)
   durable_json(out/'authorization.json',dict(authorized=True,max_calls=24,automatic_retries=False,reassign_unused=False,
    proposal_freeze_sha256=r.PROPOSAL_SHA,runtime_freeze_sha256=r.sha(root/'runtime-freeze.json'),expires_at_epoch=100,authorization_basis='FAKE TEST'))
   durable_json(out/'environment.json',dict(dafny=self.settings['dafny_version'],z3='Z3 version 4.12.1 - 64 bit',job_id='FAKE',host='fake-compute'))
   def transport(payload):
    response=self.transport(payload);index=len(self.sent)-1
    if index%4==1:response['text']='not JSON'
    if index%4==2:response['stop_reason']='max_tokens'
    response['content']=[dict(text=response['text'])]
    response['raw_response']=dict(output=dict(message=dict(content=response['content'])),
     ResponseMetadata=dict(RequestId=response['request_id'],RetryAttempts=0),usage=response['usage'],stopReason=response['stop_reason'])
    return response
   def verify(files):
    index=len(self.sent)-1
    evidence=self.verifier(files,0 if index%4==0 else 4)
    evidence.update(command=['timeout','-k','5s','60s','dafny','verify','--verify-included-files','All.dfy'],attempts=1,elapsed_seconds=0.1)
    return evidence
   rows=r.collect(out,transport,verify,100,root=root,clock=lambda:0)
   report=review(root)
   self.assertTrue(report['all24_completed']);self.assertEqual(report['verified'],6)
   self.assertEqual(report['guard_admitted'],12);self.assertEqual(report['returned'],24)
   self.assertEqual(report['outcomes'],dict(VERIFIED=6,PROOF_FAILURE=6,OUTPUT_REJECTED=6,OUTPUT_TRUNCATED=6))
   self.assertIn('Output policy/truncation review required',report['scale_up_flags'])
   original=(out/'reasoning-cal-01/request.json').read_bytes()
   (out/'reasoning-cal-01/request.json').write_bytes(original+b'\n')
   with self.assertRaises(ValueError):review(root)
   (out/'reasoning-cal-01/request.json').write_bytes(original)
   candidate=out/'reasoning-cal-01/candidate/ClientA.dfy';candidate.write_text(candidate.read_text()+'\n')
   with self.assertRaises(ValueError):review(root)

if __name__=='__main__':unittest.main(verbosity=2)
