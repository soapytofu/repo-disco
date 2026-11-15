"""Coordinator-only, bounded SSH operations for the single research session.

Never reads a credential or creates an alternative ledger. Submission ambiguity
is preserved behind a permanent exclusive lock; there is no retry/resume action.
"""
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import shlex
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parent
REMOTE = '/n/home13/sophiezeng/formal-disco/outputs/research-window-20261114'
SSH = ['ssh', '-S', str(Path.home()/'.ssh/repodisco-codex-17.sock'),
       '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=8', '-o', 'ProxyCommand=false',
       'sophiezeng@login.rc.fas.harvard.edu']
PYTHON = '/n/home13/sophiezeng/.conda/envs/repodisco/bin/python'

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def remote(code, data=None, timeout=60):
    prefix='from pathlib import Path\nROOT=Path('+repr(REMOTE)+')\n'
    p=subprocess.run(SSH+[shlex.quote(PYTHON)+' -B -c '+shlex.quote(prefix+code)],
                     input=data,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout)
    if p.stderr: print(p.stderr.decode(),file=sys.stderr)
    p.check_returncode()
    return p.stdout

def write_once(name, data):
    with (ROOT/name).open('xb') as stream: stream.write(data)

def local_pins():
    pins=json.loads((ROOT/'launch-manifest.json').read_text())['files']
    for name,h in pins.items():
        p=PurePosixPath(name)
        assert not p.is_absolute() and '..' not in p.parts
        assert not (ROOT/name).is_symlink() and sha(ROOT/name)==h,name
    return pins

def stage():
    pins=local_pins(); names=sorted(set(pins)|{'launch-manifest.json'})
    b=io.BytesIO()
    with tarfile.open(fileobj=b,mode='w:gz') as tar:
        for name in names: tar.add(ROOT/name,arcname=name,recursive=False)
    result=remote('''import hashlib,io,json,sys,tarfile
assert ROOT.is_dir() and not ROOT.is_symlink()
assert not any((ROOT/n).exists() for n in ['budget','session-001','submission-001.lock','stage-002.json'])
with tarfile.open(fileobj=io.BytesIO(sys.stdin.buffer.read()),mode='r:gz') as tar:
 for member in tar.getmembers():
  path=Path(member.name)
  assert member.isfile() and not path.is_absolute() and '..' not in path.parts
  dest=ROOT/path
  for parent in [dest,*dest.parents]:
   if parent==ROOT.parent:break
   assert not parent.is_symlink()
  data=tar.extractfile(member).read()
  if dest.exists():assert dest.is_file() and dest.read_bytes()==data,member.name
  else:
   dest.parent.mkdir(parents=True,exist_ok=True)
   with dest.open('xb') as stream:stream.write(data)
pins=json.loads((ROOT/'launch-manifest.json').read_text())['files']
for name,h in pins.items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==h,name
record=dict(files=len(pins),model_calls=0,credential_access=False,root=str(ROOT))
with (ROOT/'stage-002.json').open('x') as f:json.dump(record,f,indent=2)
print(json.dumps(record))
''',b.getvalue(),90)
    write_once('stage-002.json',result); print(result.decode())

def preflight():
    result=remote('''import hashlib,json,subprocess
launch=json.loads((ROOT/'launch-manifest.json').read_text())
for name,h in launch['files'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==h,name
assert not any((ROOT/n).exists() for n in ['budget','session-001','submission-001.lock'])
command=[str(Path.home()/'.conda/envs/repodisco/bin/python'),'-B',str(ROOT/'execution-runtime/execution_preflight.py'),
 '--work-root',str(ROOT),'--scope-sha256',launch['scope_sha256'],
 '--execution-freeze-sha256',launch['execution_freeze_sha256'],'--full-tests','--require-installed-sdk']
p=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=240)
record=dict(returncode=p.returncode,output=p.stdout,credential_access=False,model_calls=0,verifier_calls=0)
with (ROOT/'execution-preflight-001.json').open('x') as f:json.dump(record,f,indent=2)
print(json.dumps(record))
''',timeout=255)
    write_once('execution-preflight-001.json',result)
    r=json.loads(result); print(r['output']); assert r['returncode']==0

def submit():
    local_pins(); assert not (ROOT/'submission-001.json').exists()
    result=remote('''import datetime,hashlib,json,os,subprocess,time
launch=json.loads((ROOT/'launch-manifest.json').read_text())
for name,h in launch['files'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==h,name
assert json.loads((ROOT/'execution-preflight-001.json').read_text())['returncode']==0
assert not any((ROOT/n).exists() for n in ['budget','session-001','submission-001.lock','submission-001.json'])
assert time.time()<json.loads((ROOT/'scope.json').read_text())['deadline_epoch']
parts={name:subprocess.check_output(['scontrol','show','partition',name],text=True,timeout=10) for name in ['shared','sapphire']}
assert all('PreemptMode=OFF' in value and 'State=UP' in value for value in parts.values())
queue=subprocess.check_output(['squeue','-u','sophiezeng','-h','-o','%i|%Z|%j|%T'],text=True,timeout=10)
assert not any(str(ROOT) in line or 'repodisco-window' in line for line in queue.splitlines()),'Duplicate session job'
record=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),partition_evidence=parts,
 launch_manifest_sha256=hashlib.sha256((ROOT/'launch-manifest.json').read_bytes()).hexdigest(),
 maximum_window_calls=128,initial_batch_calls=32,no_requeue=True,no_retries=True)
with (ROOT/'submission-001.lock').open('x') as f:
 json.dump(record,f);f.flush();os.fsync(f.fileno())
try:
 p=subprocess.run(['sbatch','--parsable','session.sbatch'],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=25)
 record.update(returncode=p.returncode,stdout=p.stdout,stderr=p.stderr)
 if p.returncode==0:
  job=p.stdout.strip().split(';')[0];assert job.isdigit();record['job_id']=job
except subprocess.TimeoutExpired:record['ambiguous_submission']=True
with (ROOT/'submission-001.json').open('x') as f:
 json.dump(record,f,indent=2);f.flush();os.fsync(f.fileno())
print(json.dumps(record))
''',timeout=65)
    write_once('submission-001.json',result)
    print(json.dumps({k:v for k,v in json.loads(result).items() if k!='partition_evidence'},indent=2))

def status():
    result=remote('''import json,subprocess
r={}
p=ROOT/'submission-001.json'
if p.exists():
 job=json.loads(p.read_text()).get('job_id')
 if job:r['accounting']=subprocess.check_output(['sacct','-j',job,'--format=JobID,State,Elapsed,ExitCode,NodeList','-P'],text=True,timeout=12)
p=ROOT/'budget/ledger.json'
if p.exists():
 ledger=json.loads(p.read_text());rows=ledger['reservations']
 r['budget']={k:ledger[k] for k in ['terminal_reason','owner_session']}
 r['budget'].update(reserved=len(rows),completed=sum(row['status']=='COMPLETED' for row in rows),
  declared=sum(row['manifest']['max_calls'] for row in ledger['batches']))
p=ROOT/'session-001/status.json'
if p.exists():r['session']=json.loads(p.read_text())
print(json.dumps(r,indent=2))
''',timeout=35)
    print(result.decode())

if __name__=='__main__':
    assert len(sys.argv)==2 and sys.argv[1] in ['stage','preflight','submit','status']
    globals()[sys.argv[1]]()
