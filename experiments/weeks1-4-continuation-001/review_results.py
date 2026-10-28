"""Offline evidence audit; never dispatches models or invokes Dafny."""
import hashlib,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
EXP=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'experiments/repository-agent-001/guards'))
from patch import apply_text_diff
from provider_guard import parse_response as provider_parse
from branch_guard import parse_response as branch_parse

def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def files(p):return {str(f.relative_to(p)):f.read_bytes() for f in p.rglob('*.dfy')}
def hashes(fs):return {k:hashlib.sha256(v).hexdigest() for k,v in fs.items()}

def main():
 b=ROOT/'experiments/baseline-reproduction-001/smoke-001';a=ROOT/'experiments/repository-agent-001/model-001';run=EXP/'run-001'
 auth=load(EXP/'authorization.json');assert load(run/'authorization.json')==auth
 assert sha(run/'weeks14_continuation.py')==auth['driver_sha256']
 assert sha(b/'frozen/freeze.json')==auth['baseline_freeze_sha256']
 assert sha(a/'frozen/freeze.json')==auth['agent_freeze_sha256']
 bf=load(b/'frozen/freeze.json');af=load(a/'frozen/freeze.json')
 for k,v in bf['code_sha256'].items():assert sha(b/'code'/k)==v,k
 for k,v in bf['artifact_sha256'].items():assert sha(b/'frozen'/k)==v,k
 for k,v in af['code_and_input_sha256'].items():assert sha(a/'snapshot'/k)==v,k
 assert sha(a/'frozen/plan.json')==af['plan_sha256']
 ids=[];tokens={};counts={};ledgers={}
 for label,p,cap,expected in [('baseline',b,20,20),('agent',a,8,4)]:
  ledger=load(p/'requests/ledger.json');rs=ledger['reservations'];ledgers[label]=rs
  assert ledger['limit']==cap and len(rs)==expected and not ledger['closed']
  for i,r in enumerate(rs,1):
   assert r['sequence']==i and r['status']=='COMPLETED'
   response=load(p/'requests'/f'response-{i:03d}.json')
   assert response['retry_attempts']==0 and response['request_id']
   ids.append(response['request_id'])
   for k,v in response['usage'].items():tokens[k]=tokens.get(k,0)+v
  counts[label]=len(rs)
 assert len(ids)==len(set(ids))==24
 tasks=load(b/'frozen/tasks.json');br=[]
 for task,r in zip(tasks,ledgers['baseline']):
  n=task['sequence'];p=b/f'{n:02d}';row=load(p/'result.json');response=load(p/'response.json')
  assert load(p/'task.json')==task and r['prompt']==task['messages'] and r['task_id']==task['path']
  assert response==load(b/'requests'/f'response-{n:03d}.json')
  try:patched=apply_text_diff(task['source'],(p/'patch.txt').read_text())
  except ValueError:
   assert row['outcome']=='PATCH_REJECTED' and not (p/'candidate.dfy').exists()
   br.append(dict(sequence=n,outcome='PATCH_REJECTED'));continue
  assert patched==(p/'candidate.dfy').read_text()
  audit=load(p/'audit.json');assert audit['candidate_sha256']==sha(p/'candidate.dfy')
  assert audit['original_sha256']==hashlib.sha256(task['source'].encode()).hexdigest()
  v=load(p/'verification.json');assert row['strict_exit_success']==(v['exit_code']==0)
  assert row['success']==('0 errors' in v['stdout'])
  errors=re.findall(r'(\d+) errors\b',v['stdout'])
  br.append(dict(sequence=n,outcome=row['outcome'],exit_code=v['exit_code'],reported_errors=int(errors[-1]) if errors else None))
 assert load(b/'results.json')==[load(b/f'{i:02d}/result.json') for i in range(1,21)]
 ar=[]
 for (family,condition),r in zip(load(a/'frozen/plan.json')['order'],ledgers['agent']):
  name=family+'-'+condition;store=a/name;head=load(store/'HEAD.json')['revision'];rev=store/'revisions'/head;meta=load(rev/'revision.json');parent=meta['parent']
  base=files(store/'revisions'/parent/'files');accepted=files(rev/'files')
  assert base==files(a/'snapshot/experiments/repository-agent-001/fixtures'/family/(condition+'_empty'))
  assert len(list((store/'revisions').iterdir()))==2
  assert meta['source_sha256']==hashes(accepted)
  init=load(store/f'initial-verification-{parent}.json');assert init['exit_code']==4 and init['source_sha256']==hashes(base)
  attempt=store/'attempts'/r['attempt_id'];ctx=load(attempt/'context.json');response=load(attempt/'response.json')
  assert ctx['files']=={k:v.decode() for k,v in base.items()} and ctx['base_revision']==parent
  assert json.loads(r['prompt'][1]['content'])==ctx
  assert response==load(a/'requests'/f"response-{r['sequence']:03d}.json")
  assert load(attempt/'result.json')['outcome']=='SUCCESS'
  if family=='branch':
   parsed,_=branch_parse(response['text'],{k:base[k].decode() for k in ['ClientA.dfy','ClientB.dfy']})
   changes={k:v.encode() for k,v in parsed.items()}
  else:
   parsed,_=provider_parse(response['text'],base['Facts.dfy'].decode());changes={'Facts.dfy':parsed.encode()}
  assert accepted=={**base,**changes} and files(attempt/'candidate')==accepted
  v=load(attempt/'verification.json');assert v==meta['verification'] and v['exit_code']==0 and v['source_sha256']==hashes(accepted)
  assert '--verify-included-files' in v['command']
  ar.append(dict(task=name,first_attempt_success=True,guard_replayed=True,original_preserved=True,accepted_revision=head,changed_files=sorted(changes)))
 return dict(job_id='55807561',all_integrity_checks_passed=True,requests=counts,total_requests=24,unused_agent_calls=4,no_retries=True,unique_request_ids=24,usage=tokens,baseline=dict(legacy_success=7,strict_zero_exit=6,patch_rejected=9,proof_failures=3,frontend_exit_two=2,trials=br),agent=ar,scope='Bounded development smoke/integration runs; not full paper reproduction or a causal sharing comparison.')

if __name__=='__main__':
 report=main();(EXP/'results-review.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
