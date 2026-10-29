"""Offline audit of saved evidence; never dispatches or reruns verification."""
import collections,hashlib,json,sys
from pathlib import Path
import run_pilot as r
ROOT=Path(__file__).resolve().parent

def readiness(s):
 return (s['all_eight_completed'] and s['unique_request_ids']==8 and s['no_sdk_retries']
         and not s['integrity_issues'] and s['guard_admitted']==8
         and len(s['trials'])==8 and all(x.get('verifier_exit') in (0,4) for x in s['trials']))

def main():
 out=ROOT/'model-001';r.validate_bundle();r.validate_runtime()
 settings,tasks,trials=r.validate_bundle();guard=r.guard_module(ROOT)
 frozen=out/'frozen-001'
 if r.sha(frozen/'freeze.json')!=r.PROPOSAL_SHA:raise ValueError('Saved freeze mismatch')
 for n,h in r.load(frozen/'freeze.json')['files'].items():
  if r.sha(frozen/n)!=h:raise ValueError('Saved frozen byte drift')
 for n,h in r.load(out/'runtime-freeze.json')['runtime_sha256'].items():
  if r.sha(out/'runtime'/n)!=h:raise ValueError('Saved runtime byte drift')
 if r.sha(out/'runtime-freeze.json')!=r.sha(ROOT/'runtime-freeze.json'):raise ValueError('Runtime record mismatch')
 auth=r.load(out/'authorization.json')
 if auth['proposal_freeze_sha256']!=r.PROPOSAL_SHA or auth['runtime_freeze_sha256']!=r.sha(out/'runtime-freeze.json') or auth['max_calls']!=r.LIMIT or not auth['authorized'] or auth['automatic_retries'] or auth['reassign_unused']:raise ValueError('Authorization changed')
 ledger=r.load(out/'requests/ledger.json');records=ledger['reservations']
 if ledger['limit']!=r.LIMIT or len(records)>r.LIMIT:raise ValueError('Budget violation')
 rows=[];ids=[];tokens=collections.Counter();categories=collections.Counter();integrity=[]
 for index,rec in enumerate(records):
  trial=trials[index];folder=out/trial['trial_id'];task=next(t for t in tasks if t['task_id']==trial['task_id']);seed=r.sources(ROOT,task)
  messages=[dict(role='system',content=(frozen/trial['system_path']).read_text()),dict(role='user',content=(frozen/trial['prompt_path']).read_text())]
  if rec['sequence']!=index+1 or rec['task_id']!=task['task_id'] or rec['attempt_id']!=trial['trial_id'] or rec['prompt']!=messages:raise ValueError('Dispatch order/payload mismatch')
  if r.load(folder/'messages.json')!=messages or r.load(folder/'trial.json')!=trial:raise ValueError('Saved input mismatch')
  result=r.load(folder/'result.json') if (folder/'result.json').exists() else dict(outcome='INCOMPLETE_RECORD')
  row=dict(trial_id=trial['trial_id'],family=trial['family'],cell=trial['cell'],sample=trial['sample'],reservation_status=rec['status'],outcome=result['outcome'],strict_success=False,guard_admitted=False)
  if rec['status']=='COMPLETED':
   response=r.load(out/'requests'/('response-%03d.json'%(index+1)))
   if response!=r.load(folder/'response.json'):raise ValueError('Response copy differs')
   rid=response.get('request_id');ids.append(rid)
   if not isinstance(rid,str) or not rid or response.get('retry_attempts')!=0:integrity.append(trial['trial_id']+':invalid request metadata')
   for k,v in (response.get('usage') or {}).items():
    if isinstance(v,(int,float)):tokens[k]+=v
   try:edited,meta=guard.parse_response(response['text'],{n:b.decode() for n,b in seed.items()},task)
   except (ValueError,TypeError,UnicodeError,RecursionError) as error:
    row['output_rejection_reason']=str(error)
    row['output_rejection_stage']='json_or_schema' if isinstance(error,json.JSONDecodeError) or str(error) in ['Duplicate JSON key','Malformed whole-response fence','Exact editable filename/body-string set required','Response size/type'] else 'body_syntax_or_integrity'
    if result['outcome'] not in ['OUTPUT_REJECTED','REQUEST_METADATA_STOP','RESPONSE_ERROR']:raise ValueError('Guard result mismatch')
    if (folder/'accepted.json').exists():raise ValueError('Rejected output accepted')
   else:
    row['guard_admitted']=True
    if result['outcome']!='REQUEST_METADATA_STOP':
     if r.load(folder/'extraction.json')!=dict(accepted=True,**meta):raise ValueError('Extraction changed')
     row['proof_syntax_sha256']=hashlib.sha256(json.dumps(meta['syntax_trees'],sort_keys=True).encode()).hexdigest()
     candidate=dict(seed);candidate.update({n:s.encode() for n,s in edited.items()})
     saved={p.name:p.read_bytes() for p in (folder/'candidate').glob('*.dfy')}
     if candidate!=saved:raise ValueError('Saved candidate differs from guarded response')
     if r.load(folder/'candidate-hashes.json')!=dict(parent_sha256=r.hashes(seed),candidate_sha256=r.hashes(candidate)):raise ValueError('Candidate hashes')
     if (folder/'verification.json').exists():
      v=r.load(folder/'verification.json')
      if v['source_sha256']!=r.hashes(candidate) or v['command']!=['timeout','-k','5s','30s','dafny','verify','--verify-included-files','All.dfy']:raise ValueError('Verifier source/command')
      row.update(verifier_exit=v['exit_code'],verifier_seconds=v['elapsed_seconds'])
      expected={0:'VERIFIED',2:'FRONTEND_ERROR',4:'PROOF_FAILURE'}.get(v['exit_code'],'VERIFIER_STOP')
      if result['outcome']!=expected:raise ValueError('Verifier outcome/exit mismatch')
      if result['outcome']=='VERIFIED':
       if v['exit_code']!=0:raise ValueError('Invalid verification success')
       accepted=r.load(folder/'accepted.json')
       if accepted!=dict(parent_sha256=r.hashes(seed),candidate_sha256=r.hashes(candidate),editable_files=task['editable_files'],verification_sha256=r.sha(folder/'verification.json')):raise ValueError('Accepted record mismatch')
       row['strict_success']=True
      elif (folder/'accepted.json').exists():raise ValueError('Failed candidate accepted')
   row.update(request_id=rid,retry_attempts=response.get('retry_attempts'),usage=response.get('usage'),stop_reason=response.get('stop_reason'))
  categories[row['outcome']]+=1;rows.append(row)
 if len(set(ids))!=len(ids):integrity.append('duplicate request IDs')
 cells=[]
 for family in sorted({t['family'] for t in trials}):
  for cell in ['deep_shared','deep_separate']:
   rs=[x for x in rows if x['family']==family and x['cell']==cell]
   cells.append(dict(family=family,cell=cell,planned=1,reserved=len(rs),completed=sum(x['reservation_status']=='COMPLETED' for x in rs),verified=sum(x['strict_success'] for x in rs),outcomes=dict(collections.Counter(x['outcome'] for x in rs))))
 summary=dict(planned_requests=r.LIMIT,reserved=len(records),completed_responses=sum(x['reservation_status']=='COMPLETED' for x in rows),unique_request_ids=len(set(ids)),verified=sum(x['strict_success'] for x in rows),no_sdk_retries=all(x.get('retry_attempts')==0 for x in rows if x['reservation_status']=='COMPLETED'),all_eight_completed=len(rows)==r.LIMIT and all(x['reservation_status']=='COMPLETED' for x in rows),integrity_issues=integrity,request_outcomes=dict(categories),token_usage=dict(tokens),cells=cells,trials=rows,limitations='Deep-only development syntax smoke test, one sample per configuration. No depth, sharing, held-out or population effect can be inferred; shared/separate output workload differs. No pooling with a future fresh 32-trial evaluation.')
 summary['guard_admitted']=sum(x['guard_admitted'] for x in rows)
 summary['syntax_readiness']=readiness(summary)
 summary['output_rejection_reasons']=dict(collections.Counter(x.get('output_rejection_reason') for x in rows if x.get('output_rejection_reason')))
 summary['output_rejection_stages']=dict(collections.Counter(x.get('output_rejection_stage') for x in rows if x.get('output_rejection_stage')))
 (ROOT/'results-review.json').write_text(json.dumps(summary,indent=2)+'\n')
 (ROOT/'model-001-sha256.json').write_text(json.dumps({str(p.relative_to(out)):r.sha(p) for p in sorted(out.rglob('*')) if p.is_file()},indent=2)+'\n')
 print(json.dumps({k:v for k,v in summary.items() if k not in ['cells','trials']},indent=2))
 if integrity:raise SystemExit('Integrity issues require review; do not publish as accepted')
if __name__=='__main__':main()
