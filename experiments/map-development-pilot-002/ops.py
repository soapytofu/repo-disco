"""Bounded SSH operations for this one run; no retry loop or secret reading."""
import hashlib,io,json,shlex,subprocess,sys,tarfile
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parent
REMOTE='formal-disco/outputs/map-development-pilot-002'
SSH=['ssh','-S',str(Path.home()/'.ssh/repodisco-codex-14.sock'),'-o','BatchMode=yes','-o','ConnectTimeout=8','-o','ProxyCommand=false','sophiezeng@login.rc.fas.harvard.edu']

def run(code,data=None,timeout=35):
 p=subprocess.run(SSH+['python3 -c '+shlex.quote(code.replace('REMOTE_ROOT',repr(REMOTE)))],input=data,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout)
 if p.stderr:print(p.stderr.decode(),file=sys.stderr)
 p.check_returncode();return p.stdout

def stage():
 pins=json.loads((ROOT/'runtime-freeze.json').read_text())
 names=list(pins['runtime_sha256'])+['runtime-freeze.json']
 names += [str(p.relative_to(ROOT)) for p in sorted((ROOT/'frozen-001').rglob('*')) if p.is_file()]
 names += [str(p.relative_to(ROOT)) for p in sorted((ROOT/'inputs').rglob('*')) if p.is_file()]
 data=io.BytesIO()
 with tarfile.open(fileobj=data,mode='w:gz') as tar:
  for n in names:tar.add(ROOT/n,arcname=n,recursive=False)
 result=run(r'''import sys,tarfile,io,json,hashlib
from pathlib import Path,PurePosixPath
root=Path.home()/REMOTE_ROOT
root.mkdir(exist_ok=False)
with tarfile.open(fileobj=io.BytesIO(sys.stdin.buffer.read()),mode='r:gz') as tar:
 for member in tar.getmembers():
  p=PurePosixPath(member.name)
  assert member.isfile() and not p.is_absolute() and '..' not in p.parts
  dest=root/member.name;dest.parent.mkdir(parents=True,exist_ok=True)
  with dest.open('xb') as f:f.write(tar.extractfile(member).read())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
runtime=json.loads((root/'runtime-freeze.json').read_text());frozen=root/'frozen-001'
assert sha(frozen/'freeze.json')==runtime['proposal_freeze_sha256']
for n,h in runtime['runtime_sha256'].items():assert sha(root/n)==h,n
for n,h in json.loads((frozen/'freeze.json').read_text())['files'].items():assert sha(frozen/n)==h,n
for n,h in json.loads((frozen/'freeze.json').read_text())['repository_inputs_sha256'].items():assert sha(root/'inputs'/n)==h,n
print(json.dumps(dict(root=str(root),runtime_sha256=sha(root/'runtime-freeze.json'),proposal_sha256=sha(frozen/'freeze.json'),staged=True)))
''',data.getvalue(),55)
 (ROOT/'stage-001.json').write_bytes(result);print(result.decode())

def preflight():
 result=run(r'''import json,subprocess
from pathlib import Path
root=Path.home()/REMOTE_ROOT
script='set -e\nmodule load python\ncd '+str(root)+'\nexec mamba run -n repodisco python -B environment_preflight.py'
p=subprocess.run(['bash','-lc',script],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,universal_newlines=True,timeout=75)
with (root/'environment-preflight.log').open('x') as f:f.write(p.stdout)
print(json.dumps(dict(returncode=p.returncode,output=p.stdout)))
''',timeout=85)
 record=json.loads(result);(ROOT/'environment-preflight.log').write_text(record['output']);print(record['output'])
 if record['returncode']:raise SystemExit('Offline remote preflight failed; no submission')

def submit():
 auth=json.loads((ROOT/'authorization.json').read_text())
 result=run(r'''import datetime,hashlib,json,subprocess,sys,time
from pathlib import Path
root=Path.home()/REMOTE_ROOT
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not (root/'model-001').exists()
assert not list(root.glob('submission*'))
assert (Path.home()/'.repodisco-bedrock-handoff').exists()
assert (root/'environment-preflight.log').exists() and '"status": "PASS"' in (root/'environment-preflight.log').read_text()
runtime=json.loads((root/'runtime-freeze.json').read_text())
assert runtime['max_calls']==16 and not runtime['automatic_retries'] and not runtime['reassign_unused']
for n,h in runtime['runtime_sha256'].items():assert sha(root/n)==h,n
f=root/'frozen-001';assert sha(f/'freeze.json')==runtime['proposal_freeze_sha256']
for n,h in json.loads((f/'freeze.json').read_text())['files'].items():assert sha(f/n)==h,n
for n,h in json.loads((f/'freeze.json').read_text())['repository_inputs_sha256'].items():assert sha(root/'inputs'/n)==h,n
auth=json.load(sys.stdin)
assert auth['authorized'] and auth['max_calls']==16 and not auth['automatic_retries'] and not auth['reassign_unused']
assert auth['runtime_freeze_sha256']==sha(root/'runtime-freeze.json') and auth['proposal_freeze_sha256']==runtime['proposal_freeze_sha256']
assert time.time()<auth['expires_at_epoch']<=time.time()+86400
partition=subprocess.check_output(['scontrol','show','partition','test'],universal_newlines=True)
assert 'PreemptMode=OFF' in partition and 'State=UP' in partition
queue=subprocess.check_output(['squeue','-u','sophiezeng','-h','-o','%i %j %T'],universal_newlines=True)
assert 'map-bal16' not in queue
with (root/'authorization.json').open('x') as stream:json.dump(auth,stream,indent=2);stream.write('\n')
record=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),queue_before="\n".join(line for line in queue.splitlines() if "map-bal16" in line),live_partition=partition,
 authorization_sha256=sha(root/'authorization.json'),runtime_sha256=sha(root/'runtime-freeze.json'),max_calls=16,no_requeue=True,no_retries=True)
with (root/'submission.lock').open('x') as stream:json.dump(record,stream)
try:
 p=subprocess.run(['sbatch','--parsable','model.sbatch'],cwd=str(root),stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=25)
 record.update(returncode=p.returncode,stdout=p.stdout,stderr=p.stderr)
 if p.returncode==0:record['job_id']=p.stdout.strip().split(';')[0]
except subprocess.TimeoutExpired:record['ambiguous_submission']=True
with (root/'submission.json').open('x') as stream:json.dump(record,stream,indent=2);stream.write('\n')
print(json.dumps(record))
''',json.dumps(auth).encode(),40)
 (ROOT/'submission.json').write_bytes(result);print(result.decode())

def status():
 job=json.loads((ROOT/'submission.json').read_text())['job_id']
 result=run(r'''import collections,json,subprocess
from pathlib import Path
root=Path.home()/REMOTE_ROOT;out=root/'model-001'
record=dict(accounting=subprocess.check_output(['sacct','-j',JOB,'--format=JobID,State,Elapsed,ExitCode,NodeList','-P'],universal_newlines=True),output_exists=out.exists())
if (out/'requests/ledger.json').exists():
 ledger=json.loads((out/'requests/ledger.json').read_text())
 record['ledger']=dict(reserved=len(ledger['reservations']),statuses=dict(collections.Counter(r['status'] for r in ledger['reservations'])),closed=ledger['closed'])
if (out/'summary.json').exists():record['summary']={k:v for k,v in json.loads((out/'summary.json').read_text()).items() if k!='results'}
if (out/'results.json').exists():record['outcomes']=dict(collections.Counter(r['outcome'] for r in json.loads((out/'results.json').read_text())))
print(json.dumps(record))
'''.replace('JOB',repr(job)))
 print(result.decode())

def fetch():
 job=json.loads((ROOT/'submission.json').read_text())['job_id']
 data=run(r'''import io,subprocess,sys,tarfile
from pathlib import Path
root=Path.home()/REMOTE_ROOT
accounting=subprocess.check_output(['sacct','-j',JOB,'--format=JobID,State,Elapsed,ExitCode,NodeList','-P'],universal_newlines=True)
assert not any(s in accounting for s in ['RUNNING','PENDING','COMPLETING']),accounting
with (root/('accounting-'+JOB+'.txt')).open('x') as stream:stream.write(accounting)
names=['model-001','model-'+JOB+'.log','model-'+JOB+'.err','accounting-'+JOB+'.txt','submission.json','submission.lock','authorization.json','environment-preflight.log']
buffer=io.BytesIO()
with tarfile.open(fileobj=buffer,mode='w:gz') as tar:
 for n in names:
  if (root/n).exists():tar.add(root/n,arcname=n)
sys.stdout.buffer.write(buffer.getvalue())
'''.replace('JOB',repr(job)),timeout=55)
 inventory={}
 with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as tar:
  for member in tar.getmembers():
   p=PurePosixPath(member.name);assert not p.is_absolute() and '..' not in p.parts
   if member.isdir():continue
   assert member.isfile();raw=tar.extractfile(member).read();dest=ROOT/member.name
   if dest.exists() and dest.read_bytes()!=raw:
    assert member.name in ('submission.json','authorization.json') and json.loads(dest.read_text())==json.loads(raw)
    dest=ROOT/'raw-scheduler'/member.name
   if dest.exists():assert dest.read_bytes()==raw
   else:
    dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open('xb') as f:f.write(raw)
   inventory[str(dest.relative_to(ROOT))]=hashlib.sha256(raw).hexdigest()
 (ROOT/'transfer-001.json').write_text(json.dumps(dict(compressed_bytes=len(data),files=inventory),indent=2)+'\n')
 print(json.dumps(dict(files=len(inventory),compressed_bytes=len(data))))

if __name__=='__main__':
 mode=sys.argv[1]
 if mode not in ('stage','preflight','submit','status','fetch'):raise SystemExit('Unknown mode')
 globals()[mode]()
