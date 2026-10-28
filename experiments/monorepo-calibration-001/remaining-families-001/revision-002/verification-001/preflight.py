"""Verify staged calibration controls on Slurm compute; no model transport."""
import hashlib,json,os,re,shutil,socket,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'code'))
from language.dafny.repository import verify_repository

def save(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
def main():
 if not os.environ.get('SLURM_JOB_ID') or 'login' in socket.gethostname():raise SystemExit('Compute node required')
 for name,digest in json.loads((ROOT/'manifest.json').read_text()).items():
  if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:raise ValueError('Source changed: '+name)
 out=ROOT/'verification-001';out.mkdir(exist_ok=False)
 for n in ['preflight.py','build.py','tasks.json','checks.json','manifest.json']:shutil.copy2(ROOT/n,out/n)
 for n in ['code','fixtures']:shutil.copytree(ROOT/n,out/n)
 save(out/'environment.json',dict(job_id=os.environ['SLURM_JOB_ID'],host=socket.gethostname(),model_calls=0,dafny=subprocess.run(['dafny','--version'],capture_output=True,text=True,check=True).stdout.strip()))
 checks=json.loads((ROOT/'checks.json').read_text());rows=[]
 for c in checks:
  fs={f.name:f.read_bytes() for f in (ROOT/c['path']).glob('*.dfy')}
  if {n:hashlib.sha256(v).hexdigest() for n,v in fs.items()}!=c['source_sha256']:raise ValueError('Fixture hash mismatch')
  v=verify_repository(fs,'All.dfy',timeout=30).evidence;text=v['stdout']+'\n'+v['stderr']
  if c['expected']=='success':matched=v['exit_code']==0
  elif c['expected']=='proof_failure':matched=v['exit_code']==4 and any(x in text.lower() for x in ['postcondition','precondition','assertion','decreases','termination']) and 'parse errors' not in text.lower()
  else:matched=v['exit_code']==2 and 'Direct' in text and any(x in text.lower() for x in ['does not exist','unresolved','not found','not a member']) and 'parse errors' not in text.lower()
  row=dict(task_id=c['task_id'],variant=c['variant'],expected=c['expected'],matched=matched,**v);rows.append(row)
  save(out/(c['task_id']+'-'+c['variant']+'.json'),row)
  save(out/'summary.json',dict(model_calls=0,planned=len(checks),completed=len(rows),all_expected=all(r['matched'] for r in rows),results=rows))
  print(c['task_id'],c['variant'],v['exit_code'],matched,flush=True)
 if not all(r['matched'] for r in rows):raise SystemExit(1)
if __name__=='__main__':main()
