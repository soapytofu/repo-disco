"""Compute-only extension controls; never loads a provider or credential."""
import json,os,shutil,socket,subprocess,sys,hashlib
from pathlib import Path
from extension import ROOT,prepare,sources,hashes
sys.path.insert(0,str(ROOT/'code'))
from language.dafny.repository import verify_repository

def save(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
def main():
 if not os.environ.get('SLURM_JOB_ID') or 'login' in socket.gethostname():raise SystemExit('Compute allocation required')
 manifest=json.loads((ROOT/'manifest.json').read_text())
 for p,d in manifest.items():
  if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=d:raise ValueError('Hash mismatch '+p)
 out=ROOT/'verification-001';out.mkdir(exist_ok=False)
 for n in ['extension.py','preflight.py','tasks.json','plan.json','manifest.json']:shutil.copy2(ROOT/n,out/n)
 for n in ['code','guards','seeds','controls']:shutil.copytree(ROOT/n,out/n)
 save(out/'environment.json',dict(job_id=os.environ['SLURM_JOB_ID'],host=socket.gethostname(),model_calls=0,python=sys.version,dafny=subprocess.run(['dafny','--version'],capture_output=True,text=True,check=True).stdout.strip()))
 rows=[]
 def check(name,fs,expected):
  folder=out/name;folder.mkdir();src=folder/'sources';src.mkdir()
  for n,c in fs.items():(src/n).write_bytes(c)
  r=verify_repository(fs,'All.dfy',timeout=30).evidence
  matched=r['exit_code']==expected
  if expected==4:matched=matched and any(t in r['stdout'].lower() for t in ['postcondition','precondition']) and 'parse errors' not in r['stdout'].lower()
  report=dict(name=name,expected_exit=expected,matched=matched,**r);save(folder/'verification.json',report);rows.append(report)
  save(out/'summary.json',dict(model_calls=0,all_expected=all(x['matched'] for x in rows),completed=len(rows),planned=14,results=rows))
  print(name,r['category'],matched,flush=True)
 for family in ['branch','inductive']:check('seed-'+family,sources(ROOT/'seeds'/family),0)
 for task in json.loads((ROOT/'tasks.json').read_text()):
  seed=sources(ROOT/'seeds'/task['family']);before=hashes(seed)
  for label in ['reference','empty','negative']:
   result=prepare(seed,task,(ROOT/'controls'/task['id']/(label+'.json')).read_text());assert hashes(seed)==before
   check(task['id']+'-'+label,result,0 if label=='reference' else 4)
 if not all(x['matched'] for x in rows):raise SystemExit(1)
if __name__=='__main__':main()
