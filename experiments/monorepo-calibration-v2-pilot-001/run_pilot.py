"""One fresh, sequential 32-trial calibration; no resume, retry or feedback.
Offline tests inject fake transport/verifier. Import never dispatches requests.
"""
import collections,hashlib,importlib.util,json,math,os,shutil,socket,subprocess,sys,time
from pathlib import Path
sys.dont_write_bytecode=True
from bounded_requests import RequestGate,bedrock_transport,consume_key,durable_json
ROOT=Path(__file__).resolve().parent
PROPOSAL_SHA='c37781be6014e0b5ba53ae99b28a90bf7a5bf05be2cd15650098dadc3ac0a590'
LIMIT=32

def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def hashes(files):return {n:hashlib.sha256(b).hexdigest() for n,b in sorted(files.items())}
def sources(root,task):return {p.name:p.read_bytes() for p in (root/'frozen-001/tasks'/task['task_id']).glob('*.dfy')}

def validate_bundle(root=ROOT):
 f=root/'frozen-001'
 if sha(f/'freeze.json')!=PROPOSAL_SHA:raise ValueError('Proposal freeze changed')
 pins=load(f/'freeze.json')['files']
 actual={str(p.relative_to(f)) for p in f.rglob('*') if p.is_file()}
 if actual!=set(pins)|{'freeze.json'}:raise ValueError('Unexpected or missing frozen files')
 for n,h in pins.items():
  if sha(f/n)!=h:raise ValueError('Frozen bytes changed: '+n)
 settings=load(f/'settings.json');tasks=load(f/'tasks.json');trials=load(f/'trials.json')
 if settings.get('parser')!='body-json-v2.1' or settings.get('output_scope')!='JSON helper body strings; immutable host assembly':raise ValueError('Output protocol changed')
 if settings['max_calls']!=LIMIT or settings['attempts_per_sample']!=1 or settings['automatic_retries'] or settings['reassign_unused']:raise ValueError('Budget policy changed')
 if len(trials)!=32 or [t['trial_id'] for t in trials]!=['trial-%02d'%i for i in range(1,33)]:raise ValueError('Trial identity/order')
 if len(tasks)!=16 or len({t['task_id'] for t in tasks})!=16:raise ValueError('Task identity')
 if set(collections.Counter(t['task_id'] for t in trials).values())!={2}:raise ValueError('Sample count')
 for t in tasks:
  if hashes(sources(root,t))!=t['source_sha256']:raise ValueError('Seed drift')
 for t in trials:
  if sha(f/t['prompt_path'])!=t['prompt_sha256'] or sha(f/t['system_path'])!=t['system_sha256'] or not t['fresh_context'] or t['feedback']:raise ValueError('Prompt policy changed')
 return settings,tasks,trials

def validate_runtime(root=ROOT):
 r=load(root/'runtime-freeze.json')
 if r['proposal_freeze_sha256']!=PROPOSAL_SHA:raise ValueError('Runtime proposal mismatch')
 for n,h in r['runtime_sha256'].items():
  if sha(root/n)!=h:raise ValueError('Runtime changed: '+n)
 return r

def validate_authorization(root,now):
 a=load(root/'authorization.json')
 if a.get('authorized') is not True or a.get('max_calls')!=LIMIT or a.get('automatic_retries') is not False or a.get('reassign_unused') is not False:raise ValueError('32-call authorization required')
 if a.get('proposal_freeze_sha256')!=PROPOSAL_SHA or a.get('runtime_freeze_sha256')!=sha(root/'runtime-freeze.json'):raise ValueError('Authorization pins mismatch')
 expiry=a.get('expires_at_epoch')
 if type(expiry) not in (int,float) or not math.isfinite(expiry) or not now<expiry<=now+86400:raise ValueError('Expired/invalid authorization')
 if not a.get('authorization_basis'):raise ValueError('Authorization basis absent')
 return a,expiry

def guard_module(root):
 # Load only the pinned grammar. body_protocol imports it by its short name;
 # isolate that import from other experiments, then restore the caller's cache.
 directory=root/'frozen-001/guard'
 old=sys.modules.get('grammar')
 spec=importlib.util.spec_from_file_location('grammar',directory/'grammar.py')
 grammar=importlib.util.module_from_spec(spec);spec.loader.exec_module(grammar)
 sys.modules['grammar']=grammar
 try:
  spec=importlib.util.spec_from_file_location('calibration_v2_frozen_body_protocol',directory/'body_protocol.py')
  module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 finally:
  if old is None:sys.modules.pop('grammar',None)
  else:sys.modules['grammar']=old
 return module

def evaluate(task,seed,response,folder,verifier,guard):
 raw=response.get('text')
 if not isinstance(raw,str):return dict(outcome='RESPONSE_ERROR',stop=True)
 try:
  edited,decision=guard.parse_response(raw,{n:b.decode('utf-8') for n,b in seed.items()},task)
 except (ValueError,TypeError,UnicodeError,RecursionError) as error:
  durable_json(folder/'extraction.json',dict(accepted=False,error_type=type(error).__name__,reason=str(error)))
  return dict(outcome='OUTPUT_REJECTED',stop=False)
 durable_json(folder/'extraction.json',dict(accepted=True,**decision))
 candidate=dict(seed);candidate.update({n:s.encode('utf-8') for n,s in edited.items()})
 if set(candidate)!=set(seed) or any(candidate[n]!=b for n,b in seed.items() if n not in task['editable_files']):return dict(outcome='PROTECTED_SOURCE_CHANGED',stop=True)
 dest=folder/'candidate';dest.mkdir()
 for n,b in candidate.items():(dest/n).write_bytes(b)
 durable_json(folder/'candidate-hashes.json',dict(parent_sha256=hashes(seed),candidate_sha256=hashes(candidate)))
 try:evidence=verifier(candidate)
 except Exception as error:return dict(outcome='VERIFIER_ERROR',error_type=type(error).__name__,stop=True)
 durable_json(folder/'verification.json',evidence)
 if evidence.get('source_sha256')!=hashes(candidate):return dict(outcome='EVIDENCE_MISMATCH',stop=True)
 code=evidence.get('exit_code')
 if code==0:
  durable_json(folder/'accepted.json',dict(parent_sha256=hashes(seed),candidate_sha256=hashes(candidate),editable_files=task['editable_files'],verification_sha256=sha(folder/'verification.json')))
  return dict(outcome='VERIFIED',stop=False)
 if code in (2,4):return dict(outcome='FRONTEND_ERROR' if code==2 else 'PROOF_FAILURE',stop=False)
 return dict(outcome='VERIFIER_STOP',exit_code=code,stop=True)

def collect(out,transport,verifier,deadline,*,root=ROOT,clock=time.time,check_runtime=True):
 """Fresh directory supplied by CLI; this function cannot reopen a ledger."""
 out=Path(out);settings,tasks,trials=validate_bundle(root)
 if check_runtime:validate_runtime(root)
 guard=guard_module(root);gate=RequestGate(out/'requests',LIMIT,deadline,transport,clock=clock)
 rows=[];request_ids=set()
 try:
  for trial in trials:
   validate_bundle(root)
   if check_runtime:validate_runtime(root)
   task=next(t for t in tasks if t['task_id']==trial['task_id']);seed=sources(root,task);before=hashes(seed)
   folder=out/trial['trial_id'];folder.mkdir();durable_json(folder/'trial.json',trial);durable_json(folder/'task.json',task)
   messages=[dict(role='system',content=(root/'frozen-001'/trial['system_path']).read_text()),dict(role='user',content=(root/'frozen-001'/trial['prompt_path']).read_text())]
   durable_json(folder/'messages.json',messages)
   started=clock()
   try:response=gate.invoke(messages,task_id=task['task_id'],attempt_id=trial['trial_id'])
   except Exception as error:
    row=dict(**trial,outcome='REQUEST_STOP',error_type=type(error).__name__,stop=True)
    durable_json(folder/'result.json',row);rows.append(row);break
   durable_json(folder/'response.json',response)
   rid=response.get('request_id')
   if not isinstance(rid,str) or not rid or rid in request_ids or response.get('retry_attempts')!=0:
    result=dict(outcome='REQUEST_METADATA_STOP',stop=True)
   else:
    request_ids.add(rid);result=evaluate(task,seed,response,folder,verifier,guard)
   row=dict(**trial,request_id=rid,retry_attempts=response.get('retry_attempts'),usage=response.get('usage'),stop_reason=response.get('stop_reason'),elapsed_seconds=clock()-started,**result)
   if hashes(seed)!=before or hashes(sources(root,task))!=before:row.update(outcome='SEED_CHANGED',stop=True)
   durable_json(folder/'result.json',row);rows.append(row);durable_json(out/'results.json',rows)
   print(trial['trial_id'],row['outcome'],flush=True)
   if row['stop']:break
 finally:
  durable_json(out/'summary.json',dict(results=rows,maximum_calls=LIMIT,reserved_calls=len(gate.state['reservations']),completed_responses=sum(r['status']=='COMPLETED' for r in gate.state['reservations']),completed_trials=sum('request_id' in r for r in rows),verified=sum(r['outcome']=='VERIFIED' for r in rows),unused_calls_not_reassigned=LIMIT-len(gate.state['reservations']),all_trials_processed=len(rows)==LIMIT and not any(r['stop'] for r in rows)))
 return rows

def main():
 if sys.argv[1:]!=['run']:raise SystemExit('Only explicit run mode; no resume')
 if not os.environ.get('SLURM_JOB_ID') or 'login' in socket.gethostname():raise SystemExit('Compute allocation required')
 validate_bundle();pins=validate_runtime();auth,deadline=validate_authorization(ROOT,time.time())
 out=ROOT/'model-001';out.mkdir(exist_ok=False)
 durable_json(out/'authorization.json',auth);shutil.copytree(ROOT/'frozen-001',out/'frozen-001');shutil.copy2(ROOT/'runtime-freeze.json',out/'runtime-freeze.json')
 for n in pins['runtime_sha256']:
  p=out/'runtime'/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/n,p)
 sys.path.insert(0,str(ROOT/'code'))
 from language.dafny.repository import verify_repository
 from importlib.metadata import version
 env=dict(job_id=os.environ['SLURM_JOB_ID'],host=socket.gethostname(),python=sys.version,packages={p:version(p) for p in ['boto3','botocore']},dafny=subprocess.run(['dafny','--version'],capture_output=True,text=True,check=True).stdout.strip(),z3=subprocess.run(['z3','--version'],capture_output=True,text=True,check=True).stdout.strip())
 durable_json(out/'environment.json',env)
 if not env['dafny'].startswith('4.11.0') or env['z3']!='Z3 version 4.12.1 - 64 bit':raise SystemExit('Verifier version mismatch')
 consume_key(Path.home()/'.repodisco-bedrock-handoff')
 try:
  settings,_,_=validate_bundle()
  rows=collect(out,bedrock_transport(settings),lambda fs:verify_repository(fs,'All.dfy',timeout=settings['verify_timeout_seconds']).evidence,deadline)
  if len(rows)!=LIMIT or any(r['stop'] for r in rows):raise SystemExit('Stopped before all32 completed; do not resume')
 finally:os.environ.pop('AWS_BEARER_TOKEN_BEDROCK',None)
if __name__=='__main__':main()
