"""Bounded SSH operations; no credentials or model SDK. Each phase submits once."""
import hashlib,io,json,shlex,subprocess,sys,tarfile
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parent
REMOTE='formal-disco/outputs/development-restriction-001'
SSH=['ssh','-S',str(Path.home()/'.ssh/repodisco-codex-14.sock'),'-o','BatchMode=yes','-o','ConnectTimeout=8','-o','ProxyCommand=false','sophiezeng@login.rc.fas.harvard.edu']
OUT={'core':'verification-001','negatives':'verification-002'}
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
p=subprocess.run(['bash','-lc',s],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,universal_newlines=True,timeout=55)
with (root/'remote-offline-tests.log').open('x') as f:f.write(p.stdout)
print(json.dumps(dict(returncode=p.returncode,output=p.stdout)))
''',timeout=60)
 r=json.loads(result);(ROOT/'remote-offline-tests.log').write_text(r['output']);print(r['output'])
 if r['returncode']:raise SystemExit('Offline runtime tests failed')

def gate():
 path=ROOT/'verification-001-review.json';r=json.loads(path.read_text())
 assert r['phase']=='core' and r['planned']==r['matched']==8 and r['all_expected']
 assert r['manifest_sha256']==hashlib.sha256((ROOT/'manifest.json').read_bytes()).hexdigest()
 result=run('''import sys,json,hashlib
from pathlib import Path
root=Path.home()/REMOTE_ROOT;raw=sys.stdin.buffer.read();gate=json.loads(raw)
assert not (root/'submission-negatives.json').exists()
assert gate['all_expected'] and gate['planned']==gate['matched']==8
assert gate['manifest_sha256']==hashlib.sha256((root/'manifest.json').read_bytes()).hexdigest()
summary=json.loads((root/'verification-001/summary.json').read_text());assert summary['all_expected'] and summary['completed']==8
assert gate['summary_sha256']==hashlib.sha256((root/'verification-001/summary.json').read_bytes()).hexdigest()
assert gate['job_id']==json.loads((root/'verification-001/environment.json').read_text())['job_id']
with (root/'core-gate.json').open('xb') as f:f.write(raw)
print('Reviewed core gate staged; no job submitted.')
''',path.read_bytes())
 with (ROOT/'core-gate.json').open('xb') as f:f.write(path.read_bytes())
 print(result.decode())

def submit(phase):
 assert phase in OUT and not (ROOT/f'submission-{phase}.json').exists()
 code='''import datetime,hashlib,json,subprocess
from pathlib import Path
root=Path.home()/REMOTE_ROOT;phase=PHASE;out=OUTDIR
assert not (root/out).exists() and not list(root.glob('submission-'+phase+'*'))
assert 'OK' in (root/'remote-offline-tests.log').read_text()
for n,h in json.loads((root/'manifest.json').read_text()).items():assert hashlib.sha256((root/n).read_bytes()).hexdigest()==h,n
partition=subprocess.check_output(['scontrol','show','partition','test'],universal_newlines=True)
assert 'PreemptMode=OFF' in partition and 'State=UP' in partition
queue=subprocess.check_output(['squeue','-u','sophiezeng','-h','-o','%i %j %T'],universal_newlines=True)
assert 'dev-restrict-'+phase not in queue
r=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),phase=phase,live_partition=partition,queue_before=queue,model_calls=0,no_requeue=True,manifest_sha256=hashlib.sha256((root/'manifest.json').read_bytes()).hexdigest())
if phase=='negatives':
 gate=json.loads((root/'core-gate.json').read_text());assert gate['all_expected'] and gate['matched']==gate['planned']==8
 assert gate['manifest_sha256']==r['manifest_sha256'];r['core_gate_sha256']=hashlib.sha256((root/'core-gate.json').read_bytes()).hexdigest()
 assert gate['summary_sha256']==hashlib.sha256((root/'verification-001/summary.json').read_bytes()).hexdigest()
with (root/('submission-'+phase+'.lock')).open('x') as f:json.dump(r,f)
try:
 p=subprocess.run(['sbatch','--parsable','verify-'+phase+'.sbatch'],cwd=str(root),stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=25)
 r.update(returncode=p.returncode,stdout=p.stdout,stderr=p.stderr)
 if p.returncode==0:r['job_id']=p.stdout.strip().split(';')[0]
except subprocess.TimeoutExpired:r['ambiguous_submission']=True
with (root/('submission-'+phase+'.json')).open('x') as f:json.dump(r,f,indent=2);f.write('\\n')
print(json.dumps(r))
'''.replace('PHASE',repr(phase)).replace('OUTDIR',repr(OUT[phase]))
 result=run(code,timeout=40)
 with (ROOT/f'submission-{phase}.json').open('xb') as f:f.write(result)
 print(result.decode())

def status(phase):
 job=json.loads((ROOT/f'submission-{phase}.json').read_text())['job_id']
 print(run('''import json,subprocess
from pathlib import Path
root=Path.home()/REMOTE_ROOT
r=dict(accounting=subprocess.check_output(['sacct','-j',JOB,'--format=JobID,State,Elapsed,ExitCode,NodeList','-P'],universal_newlines=True))
p=root/OUTDIR/'summary.json'
if p.exists():r['summary']={k:v for k,v in json.loads(p.read_text()).items() if k!='results'}
print(json.dumps(r))
'''.replace('JOB',repr(job)).replace('OUTDIR',repr(OUT[phase]))).decode())

def fetch(phase):
 job=json.loads((ROOT/f'submission-{phase}.json').read_text())['job_id']
 data=run('''import io,subprocess,sys,tarfile
from pathlib import Path
root=Path.home()/REMOTE_ROOT;phase=PHASE
accounting=subprocess.check_output(['sacct','-j',JOB,'--format=JobID,State,Elapsed,ExitCode,NodeList','-P'],universal_newlines=True)
assert JOB+'|' in accounting and not any(s in accounting for s in ['RUNNING','PENDING','COMPLETING','CONFIGURING']),accounting
with (root/('accounting-'+JOB+'.txt')).open('x') as f:f.write(accounting)
b=io.BytesIO()
with tarfile.open(fileobj=b,mode='w:gz') as tar:
 for n in [OUTDIR,'verify-'+JOB+'.log','verify-'+JOB+'.err','accounting-'+JOB+'.txt','submission-'+phase+'.json','submission-'+phase+'.lock','remote-offline-tests.log','core-gate.json']:
  if (root/n).exists():tar.add(root/n,arcname=n)
sys.stdout.buffer.write(b.getvalue())
'''.replace('JOB',repr(job)).replace('PHASE',repr(phase)).replace('OUTDIR',repr(OUT[phase])),timeout=55)
 inventory={}
 with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as tar:
  for m in tar.getmembers():
   p=PurePosixPath(m.name);assert not p.is_absolute() and '..' not in p.parts
   if m.isdir():continue
   assert m.isfile();raw=tar.extractfile(m).read();dest=ROOT/m.name
   if dest.exists() and dest.read_bytes()!=raw:
    assert m.name==f'submission-{phase}.json' and json.loads(dest.read_text())==json.loads(raw);dest=ROOT/'raw-scheduler'/m.name
   if dest.exists():assert dest.read_bytes()==raw
   else:
    dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open('xb') as f:f.write(raw)
   inventory[str(dest.relative_to(ROOT))]=hashlib.sha256(raw).hexdigest()
 with (ROOT/f'transfer-{phase}.json').open('x') as f:json.dump(dict(compressed_bytes=len(data),files=inventory),f,indent=2);f.write('\n')
 print(json.dumps(dict(files=len(inventory),compressed_bytes=len(data))))
if __name__=='__main__':
 mode=sys.argv[1]
 if mode in ['stage','preflight','gate']:globals()[mode]()
 elif mode in ['submit','status','fetch']:globals()[mode](sys.argv[2])
 else:raise SystemExit('Unsupported operation')
