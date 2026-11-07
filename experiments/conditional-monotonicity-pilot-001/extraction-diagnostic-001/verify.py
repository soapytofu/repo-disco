"""Verify seven saved JSON proof candidates once; no model/SDK/credential code."""
import collections,hashlib,json,os,shutil,socket,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
def save(p,obj):
 with p.open('x') as f:f.write(json.dumps(obj,indent=2)+'\n')

def main():
 if sys.argv[1:]!=['verification-001']:raise SystemExit('One fixed fresh output only')
 if not os.environ.get('SLURM_JOB_ID') or 'login' in socket.gethostname():raise SystemExit('Compute allocation required')
 manifest=load(ROOT/'manifest.json')
 for n,h in manifest.items():
  if sha(ROOT/n)!=h:raise ValueError('Source drift: '+n)
 out=ROOT/'verification-001';out.mkdir(exist_ok=False)
 for n in [*manifest,'manifest.json']:
  dest=out/'snapshot'/n;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/n,dest)
 sys.path.insert(0,str(ROOT/'code'))
 from language.dafny.repository import verify_repository
 env=dict(job_id=os.environ['SLURM_JOB_ID'],host=socket.gethostname(),partition=os.environ.get('SLURM_JOB_PARTITION'),
  python=sys.version,dafny=subprocess.run(['dafny','--version'],capture_output=True,text=True,check=True,timeout=15).stdout.strip(),
  z3=subprocess.run(['z3','--version'],capture_output=True,text=True,check=True,timeout=15).stdout.strip(),model_calls=0)
 save(out/'environment.json',env)
 if env['dafny']!='4.11.0+fcb2042d6d043a2634f0854338c08feeaaaf4ae2' or env['z3']!='Z3 version 4.12.1 - 64 bit':raise ValueError('Verifier version drift')
 rows=[]
 for case in load(ROOT/'cases.json'):
  files={p.name:p.read_bytes() for p in (ROOT/case['path']).glob('*.dfy')}
  hashes={n:hashlib.sha256(b).hexdigest() for n,b in files.items()}
  if hashes!=case['candidate_sha256']:raise ValueError('Candidate drift')
  evidence=verify_repository(files,'All.dfy',timeout=60).evidence
  if evidence['source_sha256']!=hashes:raise ValueError('Evidence/source mismatch')
  record=dict(case=case,evidence=evidence,model_calls=0)
  save(out/(case['case_id']+'.json'),record);rows.append(record)
  print(case['case_id'],evidence['exit_code'],evidence['category'],flush=True)
  if evidence['exit_code'] not in (0,2,4):raise SystemExit('Infrastructure stop; no automatic retry')
 save(out/'summary.json',dict(completed_cases=len(rows),model_calls=0,results=rows,
  exit_counts=dict(collections.Counter(str(row['evidence']['exit_code']) for row in rows)),
  original_pilot_score='1/8 unchanged',no_retrospective_acceptance=True))
if __name__=='__main__':main()
