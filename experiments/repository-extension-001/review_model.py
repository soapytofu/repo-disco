"""Offline integrity review of the four saved model trials; no live calls."""
import hashlib,json,re
from extension import ROOT,prepare,sources,hashes

def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 out=ROOT/'model-001';freeze=load(out/'frozen-001/freeze.json');runtime=load(out/'runtime-freeze.json');auth=load(out/'authorization.json')
 assert auth==load(ROOT/'authorization.json') and auth['authorized'] and auth['max_calls']==4
 assert sha(out/'frozen-001/freeze.json')==auth['proposal_freeze_sha256']
 assert sha(out/'runtime-freeze.json')==auth['runtime_freeze_sha256']
 for name,digest in freeze['artifact_sha256'].items():assert sha(out/'frozen-001'/name)==digest,name
 pinned={**freeze['source_sha256'],**runtime['runtime_sha256']}
 for name,digest in pinned.items():assert sha(out/'snapshot'/name)==digest,name
 assert runtime['proposal_freeze_sha256']==sha(out/'frozen-001/freeze.json')
 ledger=load(out/'requests/ledger.json');rs=ledger['reservations'];assert ledger['limit']==4 and len(rs)==4 and not ledger['closed']
 prompts=load(out/'frozen-001/prompts.json');tasks=load(out/'snapshot/tasks.json');ids=[];usage={};rows=[]
 for n,(reservation,prompt) in enumerate(zip(rs,prompts),1):
  assert reservation['sequence']==n and reservation['status']=='COMPLETED' and reservation['attempt_id']=='1'
  assert reservation['prompt']==prompt['messages'] and reservation['task_id']==prompt['task_id']
  folder=out/f'{n:02d}';task=next(t for t in tasks if t['id']==prompt['task_id']);assert load(folder/'task.json')==task
  seed=sources(out/'snapshot/seeds'/task['family']);assert hashes(seed)==task['seed_sha256']
  response=load(folder/'response.json');assert response==load(out/'requests'/f'response-{n:03d}.json')
  assert response['retry_attempts']==0 and response['stop_reason']=='end_turn'
  ids.append(response['request_id'])
  for k,v in response['usage'].items():usage[k]=usage.get(k,0)+v
  candidate=prepare(seed,task,response['text']);assert candidate==sources(folder/'candidate')
  assert set(candidate)-set(seed)=={'ClientC.dfy'}
  for name,data in seed.items():assert candidate[name]==(data+b'include "ClientC.dfy"\n' if name=='All.dfy' else data)
  v=load(folder/'verification.json');accepted=load(folder/'accepted.json');result=load(folder/'result.json')
  assert v['exit_code']==0 and v['category']=='success' and v['source_sha256']==hashes(candidate)
  assert '--verify-included-files' in v['command'] and re.search(r'\b0 errors\b',v['stdout'])
  assert accepted['candidate_sha256']==hashes(candidate) and accepted['seed_sha256']==hashes(seed)
  assert accepted['seed_revision']==task['seed_revision'] and accepted['verification_sha256']==sha(folder/'verification.json')
  assert result==dict(task_id=task['id'],outcome='VERIFIED_EXTENSION',stop=False)
  rows.append(dict(sequence=n,task_id=task['id'],request_id=response['request_id'],outcome=result['outcome'],seed_revision=task['seed_revision'],guard_replayed=True,protected_seed_preserved=True,exit_code=0,candidate_sha256=hashes(candidate)))
 assert len(ids)==len(set(ids))==4 and all(ids)
 prior=[]
 for p in [ROOT.parent/'baseline-reproduction-001/smoke-001/requests',ROOT.parent/'repository-agent-001/model-001/requests']:
  prior += [load(f)['request_id'] for f in p.glob('response-*.json')]
 assert len(prior)==24 and not set(ids)&set(prior)
 assert load(out/'summary.json')['verified_extensions']==4 and load(out/'summary.json')['reserved_calls']==4
 assert load(out/'environment.json')['job_id']=='55813370'
 report=dict(job_id='55813370',all_integrity_checks_passed=True,actual_requests=4,unique_new_request_ids=4,automatic_retries=0,verified_extensions=4,distinct_seed_repositories=2,new_client_modules=4,pinned_files_checked=len(pinned),usage=usage,results=rows,limits='Four independent contract-guided extensions of two development seeds; no open-ended repository synthesis, independent-family generalization or causal sharing claim.')
 (ROOT/'model-review.json').write_text(json.dumps(report,indent=2)+'\n')
 manifest={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file()}
 (ROOT/'model-001-sha256.json').write_text(json.dumps(manifest,indent=2)+'\n')
 print(json.dumps({k:v for k,v in report.items() if k!='results'},indent=2))
if __name__=='__main__':main()
