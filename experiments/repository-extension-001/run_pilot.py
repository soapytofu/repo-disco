"""Four fixed new-client trials; CLI requires separate explicit authorization.

Offline tests inject transport/verifier. No request is dispatched by import.
"""
import hashlib,json,os,shutil,socket,subprocess,sys,time
from pathlib import Path
from extension import ROOT,prepare,sources,hashes
from bounded_requests import RequestGate,bedrock_transport,consume_key,durable_json

def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def validate_bundle():
 bundle=ROOT/'frozen-001';record=load(bundle/'freeze.json')
 for name,digest in record['artifact_sha256'].items():
  if sha(bundle/name)!=digest:raise ValueError('Frozen artifact changed')
 for name,digest in record['source_sha256'].items():
  if sha(ROOT/name)!=digest:raise ValueError('Frozen source changed')
 settings=load(bundle/'settings.json');tasks=load(ROOT/'tasks.json');prompts=load(bundle/'prompts.json')
 if settings['max_calls']!=4 or settings['attempts_per_task']!=1 or settings['automatic_retries'] or settings['reassign_unused']:raise ValueError('Budget changed')
 if len(prompts)!=4 or [p['task_id'] for p in prompts]!=record['request_order'] or len({p['task_id'] for p in prompts})!=4:raise ValueError('Trial order mismatch')
 if [p['sequence'] for p in prompts]!=[1,2,3,4]:raise ValueError('Sequence mismatch')
 if {t['id'] for t in tasks}!={p['task_id'] for p in prompts}:raise ValueError('Task mismatch')
 for p in prompts:
  t=next(t for t in tasks if t['id']==p['task_id'])
  if p['seed_sha256']!=t['seed_sha256'] or hashes(sources(ROOT/'seeds'/t['family']))!=t['seed_sha256']:raise ValueError('Seed mismatch')
 return settings,tasks,prompts

def validate_runtime():
 record=load(ROOT/'runtime-freeze.json')
 for name,digest in record['runtime_sha256'].items():
  if sha(ROOT/name)!=digest:raise ValueError('Runtime changed')
 if sha(ROOT/'frozen-001/freeze.json')!=record['proposal_freeze_sha256']:raise ValueError('Proposal changed')
 return record

def validate_authorization(auth,now):
 if auth.get('authorized') is not True or auth.get('max_calls')!=4 or auth.get('automatic_retries') is not False or auth.get('reassign_unused') is not False:raise ValueError('Explicit four-call authorization required')
 if auth.get('proposal_freeze_sha256')!=sha(ROOT/'frozen-001/freeze.json') or auth.get('runtime_freeze_sha256')!=sha(ROOT/'runtime-freeze.json'):raise ValueError('Authorization hash mismatch')
 expiry=auth.get('expires_at_epoch')
 if not isinstance(expiry,(int,float)) or not now < expiry <= now+86400:raise ValueError('Expired or overly long authorization')
 if not isinstance(auth.get('authorization_basis'),str) or not auth['authorization_basis'].strip():raise ValueError('Authorization evidence required')
 return min(expiry,now+1800)

def evaluate(task,seed,response,folder,verifier):
 raw=response.get('text')
 if not isinstance(raw,str):return dict(outcome='RESPONSE_ERROR',stop=True)
 try:candidate=prepare(seed,task,raw)
 except (ValueError,TypeError):return dict(outcome='EDIT_REJECTED',stop=False)
 dest=folder/'candidate';dest.mkdir()
 for name,content in candidate.items():(dest/name).write_bytes(content)
 try:evidence=verifier(candidate)
 except Exception as error:return dict(outcome='VERIFIER_ERROR',error_type=type(error).__name__,stop=True)
 durable_json(folder/'verification.json',evidence)
 if evidence.get('source_sha256')!=hashes(candidate):return dict(outcome='EVIDENCE_MISMATCH',stop=True)
 code=evidence.get('exit_code')
 if code==0:
  accepted=dict(seed_revision=task['seed_revision'],seed_sha256=hashes(seed),candidate_sha256=hashes(candidate),new_file='ClientC.dfy',entry='All.dfy',verification_sha256=sha(folder/'verification.json'))
  durable_json(folder/'accepted.json',accepted)
  return dict(outcome='VERIFIED_EXTENSION',stop=False)
 if code in (2,4):return dict(outcome='FRONTEND_ERROR' if code==2 else 'PROOF_FAILURE',stop=False)
 return dict(outcome='VERIFIER_STOP',exit_code=code,stop=True)

def validate_execution():
 validate_runtime()
 return validate_bundle()

def collect(out,transport,verifier,deadline,*,clock=time.time,check=validate_execution):
 """Caller has exclusively created out. Always uses fresh ledger; never resumes."""
 out=Path(out);settings,tasks,prompts=check()
 gate=RequestGate(out/'requests',4,deadline,transport,clock=clock);rows=[]
 try:
  for prompt in prompts:
   # Recheck the fixed bundle before each dispatch, even after a previous success.
   check();task=next(t for t in tasks if t['id']==prompt['task_id']);seed=sources(ROOT/'seeds'/task['family']);before=hashes(seed)
   folder=out/f"{prompt['sequence']:02d}";folder.mkdir();durable_json(folder/'task.json',task)
   try:response=gate.invoke(prompt['messages'],task_id=task['id'],attempt_id='1')
   except Exception as error:
    row=dict(task_id=task['id'],outcome='REQUEST_STOP',error_type=type(error).__name__,stop=True)
    durable_json(folder/'result.json',row);rows.append(row);break
   durable_json(folder/'response.json',response)
   row=dict(task_id=task['id'],**evaluate(task,seed,response,folder,verifier))
   if hashes(seed)!=before or hashes(sources(ROOT/'seeds'/task['family']))!=before:
    row=dict(task_id=task['id'],outcome='SEED_CHANGED',stop=True)
   durable_json(folder/'result.json',row);rows.append(row)
   durable_json(out/'results.json',rows)
   if row['stop']:break
 finally:
  durable_json(out/'summary.json',dict(results=rows,reserved_calls=len(gate.state['reservations']),maximum_calls=4,completed_trials=len(rows),verified_extensions=sum(r['outcome']=='VERIFIED_EXTENSION' for r in rows),unused_calls_not_reassigned=4-len(gate.state['reservations'])))
 return rows

def main():
 if sys.argv[1:]!=['run']:raise SystemExit('Only explicit run mode is supported; never resumes')
 if not os.environ.get('SLURM_JOB_ID') or 'login' in socket.gethostname():raise SystemExit('Compute allocation required')
 validate_bundle();validate_runtime()
 auth=load(ROOT/'authorization.json');deadline=validate_authorization(auth,time.time())
 out=ROOT/'model-001';out.mkdir(exist_ok=False)
 durable_json(out/'authorization.json',auth)
 shutil.copytree(ROOT/'frozen-001',out/'frozen-001')
 pins=load(ROOT/'runtime-freeze.json');shutil.copy2(ROOT/'runtime-freeze.json',out/'runtime-freeze.json')
 for name in set(pins['runtime_sha256'])|set(load(ROOT/'frozen-001/freeze.json')['source_sha256']):
  dest=out/'snapshot'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,dest)
 sys.path.insert(0,str(ROOT/'code'))
 from language.dafny.repository import verify_repository
 from importlib.metadata import version
 env=dict(job_id=os.environ['SLURM_JOB_ID'],host=socket.gethostname(),python=sys.version,packages={p:version(p) for p in ['boto3','botocore']},dafny=subprocess.run(['dafny','--version'],capture_output=True,text=True,check=True).stdout.strip())
 env['z3']=subprocess.run(['z3','--version'],capture_output=True,text=True,check=True).stdout.strip()
 durable_json(out/'environment.json',env)
 if not env['dafny'].startswith('4.11.0') or env['z3']!='Z3 version 4.12.1 - 64 bit':raise SystemExit('Dafny version mismatch')
 consume_key(Path.home()/'.repodisco-bedrock-handoff')
 try:
  settings,_,_=validate_bundle()
  collect(out,bedrock_transport(settings),lambda files:verify_repository(files,'All.dfy',timeout=30).evidence,deadline)
 finally:os.environ.pop('AWS_BEARER_TOKEN_BEDROCK',None)

if __name__=='__main__':main()
