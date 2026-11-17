"""One exclusive verifier-only submission through the user-authenticated socket."""
import io,json,tarfile,sys
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parent
QUAL=ROOT.parent/'real-repository-qualification-001'
sys.path.insert(0,str(QUAL))
from phase_ops import remote,save,sha

def call(code,data=None,seconds=45):return remote("root=root.parent/'real-repository-repair-pilot-001'\n"+code,data,seconds)
CHECK="""import hashlib,json
for n,h in json.loads((root/'runtime-manifest.json').read_text()).items():assert hashlib.sha256((root/n).read_bytes()).hexdigest()==h,n
"""
def stage():
 pins=json.loads((ROOT/'runtime-manifest.json').read_bytes());buf=io.BytesIO()
 for n,h in pins.items():assert sha((ROOT/n).read_bytes())==h,n
 with tarfile.open(fileobj=buf,mode='w:gz') as t:
  for n in list(pins)+['runtime-manifest.json']:t.add(ROOT/n,arcname=n,recursive=False)
 raw=call('''import io,sys,tarfile,subprocess,json
from pathlib import PurePosixPath
assert not root.exists();root.mkdir()
with tarfile.open(fileobj=io.BytesIO(sys.stdin.buffer.read()),mode='r:gz') as t:
 for m in t.getmembers():
  p=PurePosixPath(m.name);assert m.isfile() and not p.is_absolute() and '..' not in p.parts
  target=root/p;target.parent.mkdir(parents=True,exist_ok=True)
  with target.open('xb') as f:f.write(t.extractfile(m).read())
'''+CHECK+'''
p=subprocess.run([str(Path.home()/'.conda/envs/repodisco/bin/python'),'-B','-m','unittest','discover','-s',str(root),'-p','test_policy.py','-v'],cwd=str(root),stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=45)
print(json.dumps(dict(returncode=p.returncode,stdout=p.stdout,stderr=p.stderr,model_calls=0,verifier_calls=0,manifest_sha256=hashlib.sha256((root/'runtime-manifest.json').read_bytes()).hexdigest())))
''',buf.getvalue(),60)
 save(ROOT/'stage-001.json',raw);r=json.loads(raw);print(r['stderr']);assert r['returncode']==0

def submit():
 assert not (ROOT/'submission.json').exists()
 raw=call(CHECK+'''import datetime,subprocess
assert not (root/'verification-001').exists() and not list(root.glob('submission.*'))
part=subprocess.check_output(['scontrol','show','partition','shared'],universal_newlines=True);assert 'PreemptMode=OFF' in part and 'State=UP' in part
queue=subprocess.check_output(['squeue','-u','sophiezeng','-h','-o','%i|%Z|%j|%T'],universal_newlines=True);assert not any(str(root)+'|' in line for line in queue.splitlines())
r=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),live_partition=part,prior_queue=queue,model_calls=0,no_requeue=True)
with (root/'submission.lock').open('x') as f:json.dump(r,f)
try:
 p=subprocess.run(['sbatch','--parsable','run.sbatch'],cwd=str(root),stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=25);r.update(returncode=p.returncode,stdout=p.stdout,stderr=p.stderr)
 if p.returncode==0:
  job=p.stdout.strip().split(';')[0];assert job.isdigit();r['job_id']=job
except subprocess.TimeoutExpired:r['ambiguous_submission']=True
with (root/'submission.json').open('x') as f:json.dump(r,f,indent=2)
print(json.dumps(r))
''',seconds=40);save(ROOT/'submission.json',raw);r=json.loads(raw);print(json.dumps({k:v for k,v in r.items() if k not in ('live_partition','prior_queue')}))

def status():
 job=json.loads((ROOT/'submission.json').read_bytes())['job_id']
 raw=call('job='+repr(job)+'\n'+'''import subprocess,json
r=dict(accounting=subprocess.check_output(['sacct','-j',job,'--format=JobID,State,Elapsed,ExitCode','-P'],universal_newlines=True),completed=[])
for f in (root/'verification-001').glob('*/record.json'):
 x=json.loads(f.read_text());r['completed'].append(dict(id=f.parent.name,exit_code=x['exit_code'],seconds=x['elapsed_seconds']))
if (root/'verification-001/failure.json').exists():r['failure']=json.loads((root/'verification-001/failure.json').read_text())
print(json.dumps(r))
''');print(raw.decode())

def fetch():
 job=json.loads((ROOT/'submission.json').read_bytes())['job_id'];assert not (ROOT/'transfer.json').exists()
 raw=call('job='+repr(job)+'\n'+'''import io,json,subprocess,tarfile,sys
accounting=subprocess.check_output(['sacct','-j',job,'--format=JobID,State,Elapsed,ExitCode,MaxRSS,NodeList','-P'],universal_newlines=True)
assert job+'|' in accounting and not any(s in accounting for s in ['RUNNING','PENDING','COMPLETING','CONFIGURING'])
with (root/'accounting.txt').open('x') as f:f.write(accounting)
b=io.BytesIO()
with tarfile.open(fileobj=b,mode='w:gz') as t:
 for n in ['verification-001','accounting.txt','submission.lock']+[p.name for p in root.glob('controls-'+job+'.*')]:
  if (root/n).exists():t.add(root/n,arcname=n)
sys.stdout.buffer.write(b.getvalue())
''',seconds=60)
 inv={}
 with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as t:
  for m in t.getmembers():
   n=PurePosixPath(m.name);assert not n.is_absolute() and '..' not in n.parts
   if m.isdir():continue
   assert m.isfile();data=t.extractfile(m).read();save(ROOT/n,data);inv[str(n)]=sha(data)
 save(ROOT/'transfer.json',json.dumps(dict(files=inv,compressed_bytes=len(raw)),indent=2).encode());print(json.dumps(dict(files=len(inv),compressed_bytes=len(raw))))
if __name__=='__main__':
 action=sys.argv[1];assert action in ['stage','submit','status','fetch'];globals()[action]()
