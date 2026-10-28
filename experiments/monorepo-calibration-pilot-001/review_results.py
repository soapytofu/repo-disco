"""Offline audit of saved evidence; never dispatches or reruns verification."""
import collections,json,sys
from pathlib import Path
import run_pilot as r
ROOT=Path(__file__).resolve().parent

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
 if auth['proposal_freeze_sha256']!=r.PROPOSAL_SHA or auth['runtime_freeze_sha256']!=r.sha(out/'runtime-freeze.json') or auth['max_calls']!=32 or not auth['authorized'] or auth['automatic_retries'] or auth['reassign_unused']:raise ValueError('Authorization changed')
 ledger=r.load(out/'requests/ledger.json');records=ledger['reservations']
 if ledger['limit']!=32 or len(records)>32:raise ValueError('Budget violation')
 rows=[];ids=[];tokens=collections.Counter();categories=collections.Counter();integrity=[]
 for index,rec in enumerate(records):
  trial=trials[index];folder=out/trial['trial_id'];task=next(t for t in tasks if t['task_id']==trial['task_id']);seed=r.sources(ROOT,task)
  messages=[dict(role='system',content=(frozen/trial['system_path']).read_text()),dict(role='user',content=(frozen/trial['prompt_path']).read_text())]
  if rec['sequence']!=index+1 or rec['task_id']!=task['task_id'] or rec['attempt_id']!=trial['trial_id'] or rec['prompt']!=messages:raise ValueError('Dispatch order/payload mismatch')
  if r.load(folder/'messages.json')!=messages or r.load(folder/'trial.json')!=trial:raise ValueError('Saved input mismatch')
  result=r.load(folder/'result.json') if (folder/'result.json').exists() else dict(outcome='INCOMPLETE_RECORD')
  row=dict(trial_id=trial['trial_id'],family=trial['family'],cell=trial['cell'],sample=trial['sample'],reservation_status=rec['status'],outcome=result['outcome'],strict_success=False)
  if rec['status']=='COMPLETED':
   response=r.load(out/'requests'/('response-%03d.json'%(index+1)))
   if response!=r.load(folder/'response.json'):raise ValueError('Response copy differs')
   rid=response.get('request_id');ids.append(rid)
   if not isinstance(rid,str) or not rid or response.get('retry_attempts')!=0:integrity.append(trial['trial_id']+':invalid request metadata')
   for k,v in (response.get('usage') or {}).items():
    if isinstance(v,(int,float)):tokens[k]+=v
   try:edited,meta=guard.parse_response(response['text'],{n:b.decode() for n,b in seed.items()},task)
   except (ValueError,TypeError,UnicodeError,RecursionError):
    if result['outcome'] not in ['OUTPUT_REJECTED','REQUEST_METADATA_STOP','RESPONSE_ERROR']:raise ValueError('Guard result mismatch')
    if (folder/'accepted.json').exists():raise ValueError('Rejected output accepted')
   else:
    if result['outcome']!='REQUEST_METADATA_STOP':
     if r.load(folder/'extraction.json')!=dict(accepted=True,**meta):raise ValueError('Extraction changed')
     candidate=dict(seed);candidate.update({n:s.encode() for n,s in edited.items()})
     saved={p.name:p.read_bytes() for p in (folder/'candidate').glob('*.dfy')}
     if candidate!=saved:raise ValueError('Saved candidate differs from guarded response')
     if r.load(folder/'candidate-hashes.json')!=dict(parent_sha256=r.hashes(seed),candidate_sha256=r.hashes(candidate)):raise ValueError('Candidate hashes')
     if (folder/'verification.json').exists():
      v=r.load(folder/'verification.json')
      if v['source_sha256']!=r.hashes(candidate) or v['command']!=['timeout','-k','5s','30s','dafny','verify','--verify-included-files','All.dfy']:raise ValueError('Verifier source/command')
      row.update(verifier_exit=v['exit_code'],verifier_seconds=v['elapsed_seconds'])
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
  for cell in ['shallow_shared','shallow_separate','deep_shared','deep_separate']:
   rs=[x for x in rows if x['family']==family and x['cell']==cell]
   cells.append(dict(family=family,cell=cell,planned=2,reserved=len(rs),completed=sum(x['reservation_status']=='COMPLETED' for x in rs),verified=sum(x['strict_success'] for x in rs),outcomes=dict(collections.Counter(x['outcome'] for x in rs))))
 summary=dict(planned_requests=32,reserved=len(records),completed_responses=sum(x['reservation_status']=='COMPLETED' for x in rows),unique_request_ids=len(set(ids)),verified=sum(x['strict_success'] for x in rows),no_sdk_retries=all(x.get('retry_attempts')==0 for x in rows if x['reservation_status']=='COMPLETED'),all32_completed=len(rows)==32 and all(x['reservation_status']=='COMPLETED' for x in rows),integrity_issues=integrity,request_outcomes=dict(categories),token_usage=dict(tokens),cells=cells,trials=rows,limitations='One development instance per family and two samples per cell. Shared/edit-count and per-family depth differences are disclosed. Descriptive calibration only; no causal, held-out or population claim.')
 (ROOT/'results-review.json').write_text(json.dumps(summary,indent=2)+'\n')
 (ROOT/'model-001-sha256.json').write_text(json.dumps({str(p.relative_to(out)):r.sha(p) for p in sorted(out.rglob('*')) if p.is_file()},indent=2)+'\n')
 print(json.dumps({k:v for k,v in summary.items() if k not in ['cells','trials']},indent=2))
 if integrity:raise SystemExit('Integrity issues require review; do not publish as accepted')
if __name__=='__main__':main()
