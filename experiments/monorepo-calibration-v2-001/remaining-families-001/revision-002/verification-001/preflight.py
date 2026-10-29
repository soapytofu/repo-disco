"""One verifier-only pass; no model library, credential access, retries or resume."""
import hashlib,json,os,shutil,socket,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'code'))
from language.dafny.repository import verify_repository
from body_protocol import parse_response
from grammar import split_seed

def save(path,data):path.write_text(json.dumps(data,indent=2)+'\n')
def sha(b):return hashlib.sha256(b).hexdigest()
def matched(check,v):
 text=(v['stdout']+'\n'+v['stderr']).lower()
 if check['expected']=='success':return v['exit_code']==0
 if check['expected']=='termination_failure':return v['exit_code']==4 and any(s in text for s in ['decreases','termination']) and 'parse errors' not in text
 if check['expected']=='proof_failure':return v['exit_code']==4 and any(s in text for s in ['postcondition','precondition','assertion','for this call']) and 'parse errors' not in text
 return v['exit_code']==2 and 'direct' in text and any(s in text for s in ['does not exist','unresolved','not found','not a member']) and 'parse errors' not in text

def main():
 if not os.environ.get('SLURM_JOB_ID') or 'login' in socket.gethostname():raise SystemExit('Slurm compute node required')
 manifest=json.loads((ROOT/'manifest.json').read_text())
 for name,h in manifest.items():
  if sha((ROOT/name).read_bytes())!=h:raise ValueError('Input drift: '+name)
 out=ROOT/'verification-001';out.mkdir(exist_ok=False)
 # Archive EVERY manifest entry; missing evidence is an audit failure.
 for name in [*manifest,'manifest.json']:
  p=out/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,p)
 save(out/'environment.json',dict(job_id=os.environ['SLURM_JOB_ID'],host=socket.gethostname(),model_calls=0,dafny=subprocess.run(['dafny','--version'],capture_output=True,text=True,check=True).stdout.strip()))
 tasks={t['task_id']:t for t in json.loads((ROOT/'tasks.json').read_text())}
 checks=json.loads((ROOT/'checks.json').read_text());rows=[]
 for check in checks:
  files={p.name:p.read_bytes() for p in (ROOT/check['path']).glob('*.dfy')}
  if {n:sha(b) for n,b in files.items()}!=check['source_sha256']:raise ValueError('Source drift')
  protocol=None
  if check['variant']=='reference':
   task=tasks[check['task_id']];seeds={p.name:p.read_text() for p in (ROOT/'fixtures'/task['task_id']/'empty').glob('*.dfy')};bodies={}
   for n in task['editable_files']:
    pre,suf=split_seed(seeds[n]);s=files[n].decode();assert s.startswith(pre) and s.endswith(suf);bodies[n]=s[len(pre):-len(suf)]
   payload=json.dumps(bodies);candidate,protocol=parse_response(payload,seeds,task)
   assert {n:s.encode() for n,s in candidate.items()}==files
   save(out/(task['task_id']+'-body-payload.json'),dict(payload=payload,decision=protocol))
  v=verify_repository(files,'All.dfy',timeout=30).evidence
  row=dict(task_id=check['task_id'],variant=check['variant'],expected=check['expected'],matched=matched(check,v),protocol_replayed=protocol is not None,**v);rows.append(row)
  save(out/(check['task_id']+'-'+check['variant']+'.json'),row)
  save(out/'summary.json',dict(model_calls=0,planned=len(checks),completed=len(rows),all_expected=all(r['matched'] for r in rows),results=rows))
  print(check['task_id'],check['variant'],v['exit_code'],row['matched'],flush=True)
  if v['exit_code'] not in (0,2,4):raise SystemExit('Infrastructure failure; stop without retries')
 if not all(r['matched'] for r in rows):raise SystemExit(1)
if __name__=='__main__':main()
