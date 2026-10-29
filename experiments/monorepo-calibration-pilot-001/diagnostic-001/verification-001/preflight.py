"""Single verifier-only pass over eleven archived responses; no model transport."""
import hashlib,json,os,shutil,socket,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'code'))
from language.dafny.repository import verify_repository

def save(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
def main():
 if not os.environ.get('SLURM_JOB_ID') or 'login' in socket.gethostname():raise SystemExit('Compute only')
 for n,h in json.loads((ROOT/'manifest.json').read_text()).items():
  if hashlib.sha256((ROOT/n).read_bytes()).hexdigest()!=h:raise ValueError('Input drift')
 out=ROOT/'verification-001';out.mkdir(exist_ok=False)
 for n in ['cases.json','guard.py','preflight.py','manifest.json']:shutil.copy2(ROOT/n,out/n)
 for n in ['code','fixtures']:shutil.copytree(ROOT/n,out/n)
 save(out/'environment.json',dict(job_id=os.environ['SLURM_JOB_ID'],host=socket.gethostname(),model_calls=0,dafny=subprocess.run(['dafny','--version'],capture_output=True,text=True,check=True).stdout.strip()))
 rows=[]
 for c in json.loads((ROOT/'cases.json').read_text()):
  fs={p.name:p.read_bytes() for p in (ROOT/c['path']).glob('*.dfy')}
  if {n:hashlib.sha256(b).hexdigest() for n,b in fs.items()}!=c['candidate_sha256']:raise ValueError('Candidate drift')
  v=verify_repository(fs,'All.dfy',timeout=30).evidence
  row=dict(trial_id=c['trial_id'],**v);rows.append(row);save(out/(c['trial_id']+'.json'),row)
  save(out/'summary.json',dict(model_calls=0,planned=11,completed=len(rows),verified=sum(r['exit_code']==0 for r in rows),original_score_unchanged='18/32',results=rows))
  print(c['trial_id'],v['exit_code'],flush=True)
  if v['exit_code'] not in (0,2,4):raise SystemExit('Infrastructure error; no retries')
if __name__=='__main__':main()
