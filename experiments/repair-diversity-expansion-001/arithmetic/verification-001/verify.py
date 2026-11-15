"""Compute-only fixed-fixture verification; no API calls or automatic retries."""
from pathlib import Path
import hashlib,json,os,re,shutil,socket,subprocess,sys,tempfile,time
ROOT=Path(__file__).resolve().parent
VERSION='4.11.0+fcb2042d6d043a2634f0854338c08feeaaaf4ae2'
COMMAND=['timeout','-k','5s','60s','dafny','verify','--verify-included-files','--log-format','csv','All.dfy']
def sha(data):return hashlib.sha256(data).hexdigest()
def load(path):return json.loads(path.read_text())
def write(path,x):path.write_text(json.dumps(x,indent=2)+'\n')
def classify(record):
 text=record['stdout']+'\n'+record['stderr'];summaries=re.findall(r'^Dafny program verifier finished with (\d+) verified, (\d+) errors?\s*$',text,re.M)
 if 'warning' in text.lower():return 'warning_or_other'
 if record['exit_code']==0 and len(summaries)==1 and int(summaries[0][0])>0 and int(summaries[0][1])==0 and ': Error:' not in text:return 'success'
 if record['exit_code']==4 and len(summaries)==1 and int(summaries[0][1])>0:
  if re.search(r'decreases|termination',text,re.I):return 'termination_failure'
  return 'proof_failure'
 if record['exit_code']==2 and re.search(r'does not exist|unresolved identifier|has not been declared|could not be resolved|no member',text,re.I):return 'resolution_failure'
 return 'other'
def verify(files):
 start=time.monotonic()
 with tempfile.TemporaryDirectory(prefix='repodisco-repair-') as d:
  folder=Path(d)
  for n,b in files.items():(folder/n).write_bytes(b)
  p=subprocess.run(COMMAND,cwd=folder,capture_output=True,text=True)
  logs={str(q.relative_to(folder)):q.read_bytes().decode() for q in sorted(folder.rglob('*.csv'))}
 return dict(command=COMMAND,exit_code=p.returncode,stdout=p.stdout,stderr=p.stderr,elapsed_seconds=time.monotonic()-start,
  source_sha256={n:sha(b) for n,b in sorted(files.items())},csv=logs,csv_sha256={n:sha(s.encode()) for n,s in logs.items()},attempts=1,model_calls=0)
def run(out):
 assert os.environ.get('SLURM_JOB_ID') and 'login' not in socket.gethostname(),'Compute allocation required'
 out=Path(out);out.mkdir(exist_ok=False)
 manifest=load(ROOT/'fixture-manifest.json')
 for n,h in manifest.items():assert sha((ROOT/n).read_bytes())==h,n
 version=subprocess.run(['dafny','--version'],capture_output=True,text=True,check=True,timeout=15).stdout.strip();assert version==VERSION
 shutil.copytree(ROOT/'fixtures',out/'fixtures')
 for n in ['tasks.json','cases.json','fixture-manifest.json','generate.py','verify.py','test_structure.py','verify.sbatch']:
  shutil.copy2(ROOT/n,out/n)
 write(out/'environment.json',dict(host=socket.gethostname(),job_id=os.environ['SLURM_JOB_ID'],partition=os.environ.get('SLURM_JOB_PARTITION'),dafny=version,model_calls=0))
 summary=[]
 for case in load(ROOT/'cases.json'):
  files={p.name:p.read_bytes() for p in sorted((ROOT/case['path']).glob('*.dfy'))};assert {n:sha(b) for n,b in files.items()}==case['source_sha256']
  record=verify(files);write(out/(case['case_id']+'.json'),record)
  actual=classify(record);diagnostic=case['primary_diagnostic'];text=(record['stdout']+'\n'+record['stderr']).lower()
  matched=actual==case['expected'] and (not diagnostic or diagnostic.lower() in text)
  summary.append(dict(case_id=case['case_id'],expected=case['expected'],actual=actual,matched=matched,evidence_sha256=sha((out/(case['case_id']+'.json')).read_bytes())))
  write(out/'summary.json',dict(all_expected=all(x['matched'] for x in summary),completed=len(summary),planned=len(load(ROOT/'cases.json')),model_calls=0,checks=summary))
  print(case['case_id'],actual,'EXPECTED' if matched else 'UNEXPECTED',flush=True)
 return all(x['matched'] for x in summary)
if __name__=='__main__':
 assert len(sys.argv)==2,'Specify one fresh evidence directory'
 raise SystemExit(0 if run(sys.argv[1]) else 1)
