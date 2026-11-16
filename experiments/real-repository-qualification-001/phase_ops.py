"""Exclusive versioned verifier phase operations; uses existing authenticated transport."""
import io,json,sys,tarfile
from pathlib import Path,PurePosixPath
from ops import remote,save,sha
BASE=Path(__file__).resolve().parent
def call(phase,code,data=None,seconds=45):
    assert phase in {'container-002','container-003','coverage-001','vest-container-002','vest-container-003','vest-coverage-001'}
    return remote('root=root/'+repr(phase)+'\n'+code,data,seconds)
CHECK='''import hashlib,json
for n,h in json.loads((root/'manifest.json').read_text()).items():assert hashlib.sha256((root/n).read_bytes()).hexdigest()==h,n
'''
def stage(phase):
    local=BASE/phase;pins=json.loads((local/'manifest.json').read_bytes());buf=io.BytesIO()
    for n,h in pins.items():assert sha((local/n).read_bytes())==h,n
    with tarfile.open(fileobj=buf,mode='w:gz') as t:
        for n in list(pins)+['manifest.json']:t.add(local/n,arcname=n,recursive=False)
    raw=call(phase,'''import io,json,sys,tarfile,subprocess
from pathlib import PurePosixPath
root.mkdir(exist_ok=False)
with tarfile.open(fileobj=io.BytesIO(sys.stdin.buffer.read()),mode='r:gz') as t:
 for m in t.getmembers():
  n=PurePosixPath(m.name);assert m.isfile() and not n.is_absolute() and '..' not in n.parts
  dest=root/n;dest.parent.mkdir(parents=True,exist_ok=True)
  with dest.open('xb') as f:f.write(t.extractfile(m).read())
'''+CHECK+'''
p=subprocess.run([str(Path.home()/'.conda/envs/repodisco/bin/python'),'-B','-c','import run'],cwd=str(root),stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=20)
print(json.dumps(dict(import_exit=p.returncode,stdout=p.stdout,stderr=p.stderr,manifest_sha256=hashlib.sha256((root/'manifest.json').read_bytes()).hexdigest())))
''',buf.getvalue(),40)
    save(local/'stage.json',raw);print(raw.decode());assert json.loads(raw)['import_exit']==0
def submit(phase):
    assert not (BASE/phase/'submission.json').exists()
    raw=call(phase,CHECK+'''import datetime,subprocess
assert not (root/'results').exists() and not list(root.glob('submission.*'))
part=subprocess.check_output(['scontrol','show','partition','shared'],universal_newlines=True)
assert 'PreemptMode=OFF' in part and 'State=UP' in part
queue=subprocess.check_output(['squeue','-u','sophiezeng','-h','-o','%i|%Z|%j|%T'],universal_newlines=True)
assert not any(str(root)+'|' in line for line in queue.splitlines())
r=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),live_partition=part,prior_queue=queue,model_calls=0)
with (root/'submission.lock').open('x') as f:json.dump(r,f)
try:
 p=subprocess.run(['sbatch','--parsable','run.sbatch'],cwd=str(root),stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=25)
 r.update(returncode=p.returncode,stdout=p.stdout,stderr=p.stderr)
 if p.returncode==0:
  job=p.stdout.strip().split(';')[0];assert job.isdigit();r['job_id']=job
except subprocess.TimeoutExpired:r['ambiguous_submission']=True
with (root/'submission.json').open('x') as f:json.dump(r,f,indent=2)
print(json.dumps(r))
''',seconds=40)
    save(BASE/phase/'submission.json',raw);r=json.loads(raw);print(json.dumps({k:v for k,v in r.items() if k not in ['live_partition','prior_queue']}))
def status(phase):
    job=json.loads((BASE/phase/'submission.json').read_bytes())['job_id']
    raw=call(phase,'job='+repr(job)+'\n'+'''import json,subprocess
r=dict(accounting=subprocess.check_output(['sacct','-j',job,'--format=JobID,State,Elapsed,ExitCode,NodeList','-P'],universal_newlines=True))
r['steps']=sorted(p.name for p in (root/'results').iterdir()) if (root/'results').exists() else []
if (root/'results/failure.json').exists():r['failure']=json.loads((root/'results/failure.json').read_text())
print(json.dumps(r))
''');print(raw.decode())
def fetch(phase):
    job=json.loads((BASE/phase/'submission.json').read_bytes())['job_id']
    raw=call(phase,'job='+repr(job)+'\n'+'''import io,json,subprocess,sys,tarfile
accounting=subprocess.check_output(['sacct','-j',job,'--format=JobID,State,Elapsed,ExitCode,MaxRSS,NodeList','-P'],universal_newlines=True)
assert job+'|' in accounting and not any(s in accounting for s in ['RUNNING','PENDING','COMPLETING','CONFIGURING']),accounting
with (root/'accounting.txt').open('x') as f:f.write(accounting)
b=io.BytesIO()
names=['results','accounting.txt','submission.lock']+[p.name for p in root.glob('*-'+job+'.*')]
with tarfile.open(fileobj=b,mode='w:gz') as t:
 for n in names:
  if (root/n).exists():t.add(root/n,arcname=n)
sys.stdout.buffer.write(b.getvalue())
''',seconds=60)
    inventory={}
    with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as t:
        for m in t.getmembers():
            n=PurePosixPath(m.name);assert not n.is_absolute() and '..' not in n.parts
            if m.isdir():continue
            assert m.isfile();data=t.extractfile(m).read();save(BASE/phase/m.name,data);inventory[m.name]=sha(data)
    save(BASE/phase/'transfer.json',json.dumps(dict(files=inventory,compressed_bytes=len(raw)),indent=2).encode());print(json.dumps(dict(files=len(inventory),compressed_bytes=len(raw))))
if __name__=='__main__':
    action,phase=sys.argv[1:];assert action in {'stage','submit','status','fetch'};globals()[action](phase)
