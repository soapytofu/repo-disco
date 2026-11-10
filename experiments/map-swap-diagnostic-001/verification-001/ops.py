"""Bounded verifier-only staging/submission/evidence retrieval, no credential access."""
import hashlib,io,json,shlex,subprocess,sys,tarfile
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parent
REMOTE='formal-disco/outputs/map-swap-diagnostic-001'
SSH=['ssh','-S',str(Path.home()/'.ssh/repodisco-codex-13.sock'),'-o','BatchMode=yes','-o','ConnectTimeout=8','-o','ProxyCommand=false','sophiezeng@login.rc.fas.harvard.edu']
def run(code,data=None,timeout=35):
 p=subprocess.run(SSH+['python3 -c '+shlex.quote(code.replace('REMOTE_ROOT',repr(REMOTE)))],input=data,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout)
 if p.stderr:print(p.stderr.decode(),file=sys.stderr)
 p.check_returncode();return p.stdout

def stage():
 names=list(json.loads((ROOT/'manifest.json').read_text()))+['manifest.json'];b=io.BytesIO()
 with tarfile.open(fileobj=b,mode='w:gz') as tar:
  for n in names:tar.add(ROOT/n,arcname=n,recursive=False)
 result=run('''import sys,tarfile,io,json,hashlib
from pathlib import Path,PurePosixPath
root=Path.home()/REMOTE_ROOT;root.mkdir(exist_ok=False)
with tarfile.open(fileobj=io.BytesIO(sys.stdin.buffer.read()),mode='r:gz') as tar:
 for m in tar.getmembers():
  p=PurePosixPath(m.name);assert m.isfile() and not p.is_absolute() and '..' not in p.parts
  dest=root/m.name;dest.parent.mkdir(parents=True,exist_ok=True)
  with dest.open('xb') as f:f.write(tar.extractfile(m).read())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for n,h in json.loads((root/'manifest.json').read_text()).items():assert sha(root/n)==h,n
print(json.dumps(dict(root=str(root),manifest_sha256=sha(root/'manifest.json'),staged=True)))
''',b.getvalue(),55)
 (ROOT/'stage.json').write_bytes(result);print(result.decode())

def preflight():
 result=run('''import json,subprocess
from pathlib import Path
root=Path.home()/REMOTE_ROOT
s='set -e\\nmodule load python\\ncd '+str(root)+'\\nexec mamba run -n repodisco python -B test_design.py'
p=subprocess.run(['bash','-lc',s],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,universal_newlines=True,timeout=75)
with (root/'remote-offline-tests.log').open('x') as f:f.write(p.stdout)
print(json.dumps(dict(returncode=p.returncode,output=p.stdout)))
''',timeout=85)
 r=json.loads(result);(ROOT/'remote-offline-tests.log').write_text(r['output']);print(r['output'])
 if r['returncode']:raise SystemExit('Offline runtime tests failed')

def submit():
 result=run('''import datetime,hashlib,json,subprocess
from pathlib import Path
root=Path.home()/REMOTE_ROOT
assert not (root/'verification-001').exists() and not list(root.glob('submission*'))
assert 'OK' in (root/'remote-offline-tests.log').read_text()
for n,h in json.loads((root/'manifest.json').read_text()).items():assert hashlib.sha256((root/n).read_bytes()).hexdigest()==h,n
partition=subprocess.check_output(['scontrol','show','partition','test'],universal_newlines=True)
assert 'PreemptMode=OFF' in partition and 'State=UP' in partition
queue=subprocess.check_output(['squeue','-u','sophiezeng','-h','-o','%i %j %T'],universal_newlines=True)
assert 'map-swap-diag' not in queue
r=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),live_partition=partition,queue_before=[line for line in queue.splitlines() if "map-swap-diag" in line],model_calls=0,no_requeue=True,manifest_sha256=hashlib.sha256((root/'manifest.json').read_bytes()).hexdigest())
with (root/'submission.lock').open('x') as f:json.dump(r,f)
try:
 p=subprocess.run(['sbatch','--parsable','verify.sbatch'],cwd=str(root),stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=25)
 r.update(returncode=p.returncode,stdout=p.stdout,stderr=p.stderr)
 if p.returncode==0:r['job_id']=p.stdout.strip().split(';')[0]
except subprocess.TimeoutExpired:r['ambiguous_submission']=True
with (root/'submission.json').open('x') as f:json.dump(r,f,indent=2);f.write('\\n')
print(json.dumps(r))
''',timeout=40)
 (ROOT/'submission.json').write_bytes(result);print(result.decode())

def status():
 job=json.loads((ROOT/'submission.json').read_text())['job_id']
 print(run('''import json,subprocess
from pathlib import Path
root=Path.home()/REMOTE_ROOT
r=dict(accounting=subprocess.check_output(['sacct','-j',JOB,'--format=JobID,State,Elapsed,ExitCode,NodeList','-P'],universal_newlines=True))
p=root/'verification-001/summary.json'
if p.exists():r['summary']={k:v for k,v in json.loads(p.read_text()).items() if k!='results'}
print(json.dumps(r))
'''.replace('JOB',repr(job))).decode())

def fetch():
 job=json.loads((ROOT/'submission.json').read_text())['job_id']
 data=run('''import io,subprocess,sys,tarfile
from pathlib import Path
root=Path.home()/REMOTE_ROOT
accounting=subprocess.check_output(['sacct','-j',JOB,'--format=JobID,State,Elapsed,ExitCode,NodeList','-P'],universal_newlines=True)
assert not any(s in accounting for s in ['RUNNING','PENDING','COMPLETING']),accounting
with (root/('accounting-'+JOB+'.txt')).open('x') as f:f.write(accounting)
b=io.BytesIO()
with tarfile.open(fileobj=b,mode='w:gz') as tar:
 for n in ['verification-001','verify-'+JOB+'.log','verify-'+JOB+'.err','accounting-'+JOB+'.txt','submission.json','submission.lock','remote-offline-tests.log']:
  if (root/n).exists():tar.add(root/n,arcname=n)
sys.stdout.buffer.write(b.getvalue())
'''.replace('JOB',repr(job)),timeout=55)
 inventory={}
 with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as tar:
  for m in tar.getmembers():
   p=PurePosixPath(m.name);assert not p.is_absolute() and '..' not in p.parts
   if m.isdir():continue
   assert m.isfile();raw=tar.extractfile(m).read();dest=ROOT/m.name
   if dest.exists() and dest.read_bytes()!=raw:
    assert m.name=='submission.json' and json.loads(dest.read_text())==json.loads(raw);dest=ROOT/'raw-scheduler'/m.name
   if dest.exists():assert dest.read_bytes()==raw
   else:
    dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open('xb') as f:f.write(raw)
   inventory[str(dest.relative_to(ROOT))]=hashlib.sha256(raw).hexdigest()
 (ROOT/'transfer.json').write_text(json.dumps(dict(compressed_bytes=len(data),files=inventory),indent=2)+'\n')
 print(json.dumps(dict(files=len(inventory),compressed_bytes=len(data))))
if __name__=='__main__':
 mode=sys.argv[1]
 if mode not in ['stage','preflight','submit','status','fetch']:raise SystemExit('Unsupported operation')
 globals()[mode]()
