"""Coordinator-only bounded operations for versioned verifier-only task bundles."""
import hashlib,io,json,shlex,subprocess,sys,tarfile
from pathlib import Path,PurePosixPath
BASE=Path(__file__).resolve().parent
SSH=['ssh','-S',str(Path.home()/'.ssh/repodisco-codex-17.sock'),'-o','BatchMode=yes','-o','ConnectTimeout=8','-o','ProxyCommand=false','sophiezeng@login.rc.fas.harvard.edu']
def digest(b):return hashlib.sha256(b).hexdigest()
def run(root,code,data=None,timeout=45):
 code='ROOT_REL='+repr('formal-disco/outputs/repository-repair-selection-001/'+str(root.relative_to(BASE)))+'\n'+code
 p=subprocess.run(SSH+['python3 -c '+shlex.quote(code)],input=data,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout)
 if p.stderr:print(p.stderr.decode(),file=sys.stderr)
 p.check_returncode();return p.stdout

def pins(root):
 runtime=json.loads((root/'runtime-manifest.json').read_text());fixtures=json.loads((root/'fixture-manifest.json').read_text());allpins={**runtime,**fixtures}
 for n,h in allpins.items():
  p=PurePosixPath(n);assert not p.is_absolute() and '..' not in p.parts
  assert digest((root/n).read_bytes())==h,n
 return allpins

def stage(root):
 names=list(pins(root))+['runtime-manifest.json'];buf=io.BytesIO()
 with tarfile.open(fileobj=buf,mode='w:gz') as tar:
  for n in sorted(set(names)):tar.add(root/n,arcname=n,recursive=False)
 raw=run(root,'''import hashlib,io,json,sys,tarfile
from pathlib import Path,PurePosixPath
root=Path.home()/ROOT_REL;root.mkdir(parents=True,exist_ok=False)
with tarfile.open(fileobj=io.BytesIO(sys.stdin.buffer.read()),mode='r:gz') as tar:
 for m in tar.getmembers():
  p=PurePosixPath(m.name);assert m.isfile() and not p.is_absolute() and '..' not in p.parts
  dest=root/m.name;dest.parent.mkdir(parents=True,exist_ok=True)
  with dest.open('xb') as f:f.write(tar.extractfile(m).read())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for manifest in ['runtime-manifest.json','fixture-manifest.json']:
 for n,h in json.loads((root/manifest).read_text()).items():assert sha(root/n)==h,n
print(json.dumps(dict(root=str(root),runtime_manifest_sha256=sha(root/'runtime-manifest.json'),fixture_manifest_sha256=sha(root/'fixture-manifest.json'),model_calls=0)))
''',buf.getvalue(),60)
 with (root/'stage-001.json').open('xb') as f:f.write(raw)
 print(raw.decode())

def preflight(root):
 raw=run(root,'''import json,subprocess
from pathlib import Path
root=Path.home()/ROOT_REL
p=subprocess.run([str(Path.home()/'.conda/envs/repodisco/bin/python'),'-B','test_structure.py'],cwd=str(root),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,universal_newlines=True,timeout=55)
with (root/'remote-offline-tests.log').open('x') as f:f.write(p.stdout)
print(json.dumps(dict(returncode=p.returncode,output=p.stdout)))
''',timeout=60);r=json.loads(raw)
 with (root/'remote-offline-tests.log').open('x') as f:f.write(r['output'])
 print(r['output']);assert r['returncode']==0

def submit(root):
 assert not (root/'submission-001.json').exists();pins(root)
 raw=run(root,'''import datetime,hashlib,json,subprocess
from pathlib import Path
root=Path.home()/ROOT_REL
assert not (root/'verification-001').exists() and not list(root.glob('submission-001*'))
assert 'OK' in (root/'remote-offline-tests.log').read_text()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for manifest in ['runtime-manifest.json','fixture-manifest.json']:
 for n,h in json.loads((root/manifest).read_text()).items():assert sha(root/n)==h,n
part=subprocess.check_output(['scontrol','show','partition','test'],universal_newlines=True)
assert 'PreemptMode=OFF' in part and 'State=UP' in part
queue=subprocess.check_output(['squeue','-u','sophiezeng','-h','-o','%i|%Z|%j|%T'],universal_newlines=True)
assert not any(str(root) in line for line in queue.splitlines()),'Existing job in same workspace'
r=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),live_partition=part,duplicate_workspace_jobs=[],runtime_manifest_sha256=sha(root/'runtime-manifest.json'),fixture_manifest_sha256=sha(root/'fixture-manifest.json'),model_calls=0,no_requeue=True)
with (root/'submission-001.lock').open('x') as f:json.dump(r,f)
try:
 p=subprocess.run(['sbatch','--parsable','verify.sbatch'],cwd=str(root),stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=25)
 r.update(returncode=p.returncode,stdout=p.stdout,stderr=p.stderr)
 if p.returncode==0:
  job=p.stdout.strip().split(';')[0];assert job.isdigit();r['job_id']=job
except subprocess.TimeoutExpired:r['ambiguous_submission']=True
with (root/'submission-001.json').open('x') as f:json.dump(r,f,indent=2);f.write('\\n')
print(json.dumps(r))
''',timeout=40)
 with (root/'submission-001.json').open('xb') as f:f.write(raw)
 r=json.loads(raw);print(json.dumps({k:v for k,v in r.items() if k!='live_partition'}))

def status(root):
 job=json.loads((root/'submission-001.json').read_text())['job_id']
 raw=run(root,'''import json,subprocess
from pathlib import Path
root=Path.home()/ROOT_REL
r=dict(accounting=subprocess.check_output(['sacct','-j',JOB,'--format=JobID,State,Elapsed,ExitCode,NodeList','-P'],universal_newlines=True))
p=root/'verification-001/summary.json'
if p.exists():r['summary']={k:v for k,v in json.loads(p.read_text()).items() if k not in ['checks','results']}
print(json.dumps(r))
'''.replace('JOB',repr(job)))
 print(raw.decode())

def fetch(root):
 job=json.loads((root/'submission-001.json').read_text())['job_id']
 raw=run(root,'''import hashlib,io,json,subprocess,sys,tarfile
from pathlib import Path
root=Path.home()/ROOT_REL
accounting=subprocess.check_output(['sacct','-j',JOB,'--format=JobID,State,Elapsed,ExitCode,NodeList','-P'],universal_newlines=True)
assert JOB+'|' in accounting and not any(x in accounting for x in ['RUNNING','PENDING','COMPLETING','CONFIGURING']),accounting
with (root/('accounting-'+JOB+'.txt')).open('x') as f:f.write(accounting)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for manifest in ['runtime-manifest.json','fixture-manifest.json']:
 for n,h in json.loads((root/manifest).read_text()).items():assert sha(root/n)==h,n
b=io.BytesIO()
with tarfile.open(fileobj=b,mode='w:gz') as tar:
 for n in ['verification-001','verify-'+JOB+'.log','verify-'+JOB+'.err','accounting-'+JOB+'.txt','submission-001.json','submission-001.lock','remote-offline-tests.log']:
  if (root/n).exists():tar.add(root/n,arcname=n)
sys.stdout.buffer.write(b.getvalue())
'''.replace('JOB',repr(job)),timeout=60)
 inventory={}
 with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as tar:
  for m in tar.getmembers():
   path=PurePosixPath(m.name);assert not path.is_absolute() and '..' not in path.parts
   if m.isdir():continue
   assert m.isfile();b=tar.extractfile(m).read();dest=root/m.name
   if dest.exists() and dest.read_bytes()!=b:
    assert m.name=='submission-001.json' and json.loads(dest.read_text())==json.loads(b);dest=root/'raw-scheduler'/m.name
   if dest.exists():assert dest.read_bytes()==b
   else:
    dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open('xb') as f:f.write(b)
   inventory[str(dest.relative_to(root))]=digest(b)
 with (root/'transfer-001.json').open('x') as f:json.dump(dict(compressed_bytes=len(raw),files=inventory),f,indent=2);f.write('\n')
 print(json.dumps(dict(files=len(inventory),compressed_bytes=len(raw))))

if __name__=='__main__':
 assert len(sys.argv)==3
 mode,rel=sys.argv[1:];root=(BASE/rel).resolve();assert root.is_relative_to(BASE) and root!=BASE
 assert mode in ['stage','preflight','submit','status','fetch']
 globals()[mode](root)
