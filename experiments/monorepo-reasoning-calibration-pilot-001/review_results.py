"""Reconstruct and audit saved evidence offline. No requests or Dafny runs."""
import collections,hashlib,json
from pathlib import Path
import run_pilot as r

def require(ok,message):
 if not ok:raise ValueError(message)

def review(root=r.ROOT):
 out=root/'model-001';settings,tasks,trials=r.validate_bundle(root);pins=r.validate_runtime(root)
 guard=r.guard_module(root);frozen=out/'frozen-001';rows=[];ids=[];tokens=collections.Counter()
 require(r.sha(frozen/'freeze.json')==r.PROPOSAL_SHA,'Archived proposal mismatch')
 for n,h in r.load(frozen/'freeze.json')['files'].items():require(r.sha(frozen/n)==h,'Archived input mismatch: '+n)
 require(r.sha(out/'runtime-freeze.json')==r.sha(root/'runtime-freeze.json'),'Runtime freeze changed')
 for n,h in pins['runtime_sha256'].items():require(r.sha(out/'runtime'/n)==h,'Archived runtime mismatch: '+n)
 auth=r.load(out/'authorization.json')
 require(auth['authorized'] and auth['max_calls']==r.LIMIT and not auth['automatic_retries'] and not auth['reassign_unused'],'Budget authorization')
 require(auth['proposal_freeze_sha256']==r.PROPOSAL_SHA and auth['runtime_freeze_sha256']==r.sha(root/'runtime-freeze.json'),'Authorization pins')
 env=r.load(out/'environment.json')
 require(env['dafny']==settings['dafny_version'] and env['z3']=='Z3 version 4.12.1 - 64 bit','Verifier version')
 require(env['job_id'] and 'login' not in env['host'],'Compute provenance')
 ledger=r.load(out/'requests/ledger.json');reservations=ledger['reservations']
 require(ledger['limit']==r.LIMIT and len(reservations)<=r.LIMIT and ledger['deadline']==auth['expires_at_epoch'],'Ledger budget/deadline')
 for index,rec in enumerate(reservations):
  trial=trials[index];task=next(t for t in tasks if t['task_id']==trial['task_id'])
  folder=out/trial['trial_id'];seed=r.sources(root,task);request=r.load(frozen/trial['request_path'])
  require(rec['sequence']==index+1 and rec['task_id']==task['task_id'] and rec['attempt_id']==trial['trial_id'],'Request order')
  require(rec['prompt']==request and r.sha(folder/'request.json')==trial['request_sha256'],'Exact request payload')
  require(r.load(folder/'trial.json')==trial and r.load(folder/'task.json')==task,'Trial metadata')
  if 'dispatch_started_at_epoch' in rec:require(rec['dispatch_started_at_epoch']<auth['expires_at_epoch'],'Dispatch deadline')
  result=r.load(folder/'result.json') if (folder/'result.json').exists() else dict(outcome='INCOMPLETE_RECORD')
  row=dict(trial_id=trial['trial_id'],task_id=task['task_id'],semantic_instance=trial['semantic_instance'],family=trial['family'],cell=trial['cell'],
   reservation_status=rec['status'],dispatch_started='dispatch_started_at_epoch' in rec,outcome=result['outcome'],guard_admitted=False,strict_success=False)
  if rec['status']=='COMPLETED':
   response=r.load(out/'requests'/('response-%03d.json'%(index+1)))
   require(response==r.load(folder/'response.json'),'Response copies differ')
   rid=response.get('request_id');ids.append(rid)
   require(isinstance(rid,str) and rid and response.get('retry_attempts')==0,'Request ID/retry metadata')
   if 'raw_response' in response:
    raw=response['raw_response']
    require(raw['ResponseMetadata']['RequestId']==rid and raw['ResponseMetadata']['RetryAttempts']==0,'Raw request metadata')
    require(raw['output']['message']['content']==response['content'],'Raw content mismatch')
    require(''.join(b['text'] for b in response['content'] if 'text' in b)==response['text'],'Extracted response text mismatch')
    require(raw.get('usage')==response.get('usage') and raw.get('stopReason')==response.get('stop_reason'),'Raw usage/stop mismatch')
   else:raise ValueError('Missing complete provider response')
   require(result.get('request_id')==rid and result.get('retry_attempts')==0,'Trial request metadata')
   for k,v in (response.get('usage') or {}).items():
    if isinstance(v,(int,float)):tokens[k]+=v
   extraction=r.load(folder/'extraction.json') if (folder/'extraction.json').exists() else {}
   if response.get('stop_reason')=='max_tokens':
    require(result['outcome']=='OUTPUT_TRUNCATED' and not extraction.get('accepted'),'Truncation scoring')
   else:
    try:candidate_text,decision=guard.parse_response(response['text'],{n:b.decode() for n,b in seed.items()},task)
    except (ValueError,TypeError,UnicodeError,RecursionError) as error:
     require(result['outcome']=='OUTPUT_REJECTED' and extraction==dict(accepted=False,error_type=type(error).__name__,reason=str(error)),'Output rejection mismatch')
     row['rejection_reason']=str(error)
    else:
     row['guard_admitted']=True
     require(extraction==dict(accepted=True,**decision),'Extraction decision mismatch')
     candidate={n:s.encode() for n,s in candidate_text.items()}
     require(candidate=={p.name:p.read_bytes() for p in (folder/'candidate').glob('*.dfy')},'Candidate differs from exact guarded response')
     require(set(candidate)==set(seed) and all(candidate[n]==b for n,b in seed.items() if n not in task['editable_files']),'Protected source changed')
     require(r.load(folder/'candidate-hashes.json')==dict(parent_sha256=r.hashes(seed),candidate_sha256=r.hashes(candidate)),'Candidate hashes')
     trees=[v['syntax'] for v in decision['bodies'].values()]
     row.update(body_bytes=sum(len(candidate[n])-len(seed[n])+1 for n in task['editable_files']),editable_bodies=len(trees),
      separate_bodies_same_syntax=(trees[0]==trees[1]) if len(trees)==2 else None,
      separate_bodies_exact_copy=len({v['body_sha256'] for v in decision['bodies'].values()})==1 if len(trees)==2 else None,
      proof_syntax_sha256=hashlib.sha256(json.dumps(trees,sort_keys=True).encode()).hexdigest())
     if (folder/'verification.json').exists():
      v=r.load(folder/'verification.json')
      require(v['source_sha256']==r.hashes(candidate),'Verifier source hashes')
      require(v['command']==['timeout','-k','5s','60s','dafny','verify','--verify-included-files','All.dfy'],'Verifier command')
      require(v['model_calls']==0 and v['attempts']==1,'Verifier attempts')
      expected={0:'VERIFIED',2:'FRONTEND_ERROR',4:'PROOF_FAILURE'}.get(v['exit_code'],'VERIFIER_STOP')
      require(result['outcome']==expected,'Strict outcome mismatch')
      diagnostic=(v['stdout']+'\n'+v['stderr']).lower()
      row.update(verifier_exit=v['exit_code'],verifier_seconds=v['elapsed_seconds'],
       diagnostics=[label for label,needle in [('parse','parse error'),('resolution','unresolved'),('precondition','precondition'),('postcondition','postcondition'),('assertion','assertion'),('termination','decreases clause')] if needle in diagnostic])
      if v['exit_code']==0:
       require(r.load(folder/'accepted.json')==dict(parent_sha256=r.hashes(seed),candidate_sha256=r.hashes(candidate),editable_files=task['editable_files'],verification_sha256=r.sha(folder/'verification.json')),'Accepted source mismatch')
       row['strict_success']=True
     else:require(result['outcome'] in ('VERIFIER_ERROR','INCOMPLETE_RECORD'),'Missing verifier evidence')
   if not row['strict_success']:require(not (folder/'accepted.json').exists(),'Invalid accepted record')
   if not row['guard_admitted']:require(not (folder/'candidate').exists() and not (folder/'verification.json').exists(),'Rejected output was verified')
   row.update(request_id=rid,retry_attempts=response['retry_attempts'],usage=response.get('usage'),stop_reason=response.get('stop_reason'))
  rows.append(row)
 require(len(set(ids))==len(ids),'Duplicate request IDs')
 summary=dict(planned_requests=r.LIMIT,reserved=len(reservations),dispatch_started=sum(row['dispatch_started'] for row in rows),
  returned=len(ids),unique_request_ids=len(set(ids)),guard_admitted=sum(row['guard_admitted'] for row in rows),verified=sum(row['strict_success'] for row in rows),
  no_sdk_retries=True,all24_completed=len(rows)==r.LIMIT and all(row['reservation_status']=='COMPLETED' and row['outcome'] in ('VERIFIED','PROOF_FAILURE','FRONTEND_ERROR','OUTPUT_REJECTED','OUTPUT_TRUNCATED') for row in rows),
  outcomes=dict(collections.Counter(row['outcome'] for row in rows)),token_usage=dict(tokens),trials=rows,main_collection_authorized=False)
 summary['cells']=[dict(family=f,cell=c,planned=2,reserved=sum(row['family']==f and row['cell']==c for row in rows),
  verified=sum(row['family']==f and row['cell']==c and row['strict_success'] for row in rows))
  for f in sorted({t['family'] for t in trials}) for c in ['shallow_shared','shallow_separate','deep_shared','deep_separate']]
 summary['instances']=[dict(instance=i,planned=4,returned=sum(row['semantic_instance']==i and row['reservation_status']=='COMPLETED' for row in rows),
  verified=sum(row['semantic_instance']==i and row['strict_success'] for row in rows)) for i in sorted({t['semantic_instance'] for t in trials})]
 summary['scale_up_flags']=[]
 if not summary['all24_completed']:summary['scale_up_flags'].append('Incomplete or ambiguous batch')
 if summary['guard_admitted']!=r.LIMIT:summary['scale_up_flags'].append('Output policy/truncation review required')
 if any(row['outcome']=='FRONTEND_ERROR' for row in rows):summary['scale_up_flags'].append('Frontend failures require review')
 for item in summary['instances']:
  if item['returned']==4 and item['verified'] in (0,4):summary['scale_up_flags'].append(item['instance']+': floor/ceiling review required')
 for family in sorted({t['family'] for t in trials}):
  family_rows=[row for row in rows if row['family']==family]
  if len(family_rows)==8 and all(row['reservation_status']=='COMPLETED' for row in family_rows):
   count=sum(row['strict_success'] for row in family_rows)
   if count in (0,8):summary['scale_up_flags'].append(family+': '+str(count)+'/8 floor/ceiling review required')
   elif count==7:summary['scale_up_flags'].append(family+': 7/8 near-ceiling review required')
 summary['limitations']='One sample per variant; six inspected development instances. Separate has two bodies and allows copying. Depth is reference-relative, not proved minimal. No causal, held-out or model-population claim; no automatic expansion.'
 saved=r.load(out/'summary.json')
 require(saved['reserved_calls']==summary['reserved'] and saved['completed_responses']==summary['returned'] and saved['verified']==summary['verified'],'Runtime summary mismatch')
 require(saved['all_trials_processed']==summary['all24_completed'],'Runtime completion mismatch')
 return summary

if __name__=='__main__':
 summary=review()
 r.durable_json(r.ROOT/'results-review.json',summary)
 out=r.ROOT/'model-001'
 r.durable_json(r.ROOT/'model-001-sha256.json',{str(p.relative_to(out)):r.sha(p) for p in sorted(out.rglob('*')) if p.is_file()})
 print(json.dumps({k:v for k,v in summary.items() if k not in ('trials','cells')},indent=2))
