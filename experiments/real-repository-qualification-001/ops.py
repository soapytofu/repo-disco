"""Bounded coordinator operations. No verifier executes on the login node."""
import hashlib,io,json,shlex,subprocess,sys,tarfile
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parent
SSH=['ssh','-S',str(Path.home()/'.ssh/repodisco-codex-18.sock'),'-o','BatchMode=yes','-o','ConnectTimeout=8','-o','ProxyCommand=false','sophiezeng@login.rc.fas.harvard.edu']
def sha(raw):return hashlib.sha256(raw).hexdigest()
def remote(code,data=None,seconds=45):
    code="from pathlib import Path\nroot=Path.home()/'formal-disco/outputs/real-repository-qualification-001'\n"+code
    p=subprocess.run(SSH+['python3 -c '+shlex.quote(code)],input=data,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=seconds)
    if p.stderr:print(p.stderr.decode(),file=sys.stderr)
    p.check_returncode();return p.stdout
def save(path,raw):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as f:f.write(raw)
def manifest():
    files=json.loads((ROOT/'runtime-manifest.json').read_bytes())
    for p in json.loads((ROOT/'source-manifest.json').read_bytes()):
        files.update({'upstream/'+p['id']+'/'+n:h for n,h in p['files'].items()})
    for n,h in files.items():assert sha((ROOT/n).read_bytes())==h,n
    return files
CHECK="""
import hashlib,json
for n,h in json.loads((root/'runtime-manifest.json').read_text()).items():assert hashlib.sha256((root/n).read_bytes()).hexdigest()==h,n
for p in json.loads((root/'source-manifest.json').read_text()):
 for n,h in p['files'].items():assert hashlib.sha256((root/'upstream'/p['id']/n).read_bytes()).hexdigest()==h,n
"""
def stage():
    files=manifest();data=io.BytesIO()
    with tarfile.open(fileobj=data,mode='w:gz') as t:
        for n in sorted(set(files)|{'runtime-manifest.json'}):t.add(ROOT/n,arcname=n,recursive=False)
    raw=remote('''import io,json,sys,tarfile
from pathlib import PurePosixPath
assert not root.exists()
root.mkdir()
with tarfile.open(fileobj=io.BytesIO(sys.stdin.buffer.read()),mode='r:gz') as t:
 for m in t.getmembers():
  p=PurePosixPath(m.name);assert m.isfile() and not p.is_absolute() and '..' not in p.parts
  dest=root/m.name;dest.parent.mkdir(parents=True,exist_ok=True)
  with dest.open('xb') as f:f.write(t.extractfile(m).read())
'''+CHECK+'''
print(json.dumps(dict(root=str(root),runtime_sha256=hashlib.sha256((root/'runtime-manifest.json').read_bytes()).hexdigest(),model_calls=0)))
''',data.getvalue(),60)
    save(ROOT/'stage-001.json',raw);print(raw.decode())
def preflight():
    raw=remote(CHECK+'''import subprocess
p=subprocess.run([str(Path.home()/'.conda/envs/repodisco/bin/python'),'-B','test_baseline.py'],cwd=str(root),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=45)
with (root/'remote-offline-tests.log').open('xb') as f:f.write(p.stdout)
print(json.dumps(dict(exit_code=p.returncode,log=p.stdout.decode())))
''',seconds=55)
    result=json.loads(raw);save(ROOT/'remote-offline-tests.log',result['log'].encode());print(result['log']);assert result['exit_code']==0
def submit(project):
    assert project in {'dafny-vmc','vest'};manifest()
    assert not (ROOT/'submissions'/('baseline-'+project+'.json')).exists()
    raw=remote(CHECK+"project="+repr(project)+'\n'+'''import datetime,subprocess
assert not (root/'results'/project).exists()
directory=root/'submissions';directory.mkdir(exist_ok=True)
stem='baseline-'+project
assert not list(directory.glob(stem+'.*'))
assert 'OK' in (root/'remote-offline-tests.log').read_text()
part=subprocess.check_output(['scontrol','show','partition','shared'],universal_newlines=True)
assert 'PreemptMode=OFF' in part and 'State=UP' in part
queue=subprocess.check_output(['squeue','-u','sophiezeng','-h','-o','%i|%Z|%j|%T'],universal_newlines=True)
name='qual-'+project
assert not any(str(root) in line and name in line for line in queue.splitlines())
r=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),project=project,live_partition=part,prior_queue=queue,model_calls=0,no_requeue=True)
with (directory/(stem+'.lock')).open('x') as f:json.dump(r,f)
try:
 p=subprocess.run(['sbatch','--parsable','--job-name='+name,'--output='+project+'-%j.log','--error='+project+'-%j.err','baseline.sbatch',project],cwd=str(root),stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=25)
 r.update(returncode=p.returncode,stdout=p.stdout,stderr=p.stderr)
 if p.returncode==0:
  job=p.stdout.strip().split(';')[0];assert job.isdigit();r['job_id']=job
except subprocess.TimeoutExpired:r['ambiguous_submission']=True
with (directory/(stem+'.json')).open('x') as f:json.dump(r,f,indent=2)
print(json.dumps(r))
''',seconds=40)
    save(ROOT/'submissions'/('baseline-'+project+'.json'),raw);r=json.loads(raw);print(json.dumps({k:v for k,v in r.items() if k not in ['live_partition','prior_queue']}))
def status(project):
    job=json.loads((ROOT/'submissions'/('baseline-'+project+'.json')).read_bytes())['job_id']
    raw=remote('import subprocess,json\n'+"project="+repr(project)+'\n'+'job='+repr(job)+'\n'+'''
r=dict(accounting=subprocess.check_output(['sacct','-j',job,'--format=JobID,State,Elapsed,ExitCode,NodeList','-P'],universal_newlines=True))
out=root/'results'/project
r['steps']=sorted(p.name for p in out.iterdir()) if out.exists() else []
if (out/'failure.json').exists():r['failure']=json.loads((out/'failure.json').read_text())
print(json.dumps(r))
''');print(raw.decode())
def fetch(project):
    job=json.loads((ROOT/'submissions'/('baseline-'+project+'.json')).read_bytes())['job_id']
    raw=remote('import hashlib,io,json,subprocess,sys,tarfile\n'+'project='+repr(project)+'\n'+'job='+repr(job)+'\n'+'''
accounting=subprocess.check_output(['sacct','-j',job,'--format=JobID,State,Elapsed,ExitCode,MaxRSS,NodeList','-P'],universal_newlines=True)
assert job+'|' in accounting and not any(s in accounting for s in ['RUNNING','PENDING','COMPLETING','CONFIGURING']),accounting
with (root/(project+'-accounting.txt')).open('x') as f:f.write(accounting)
data=io.BytesIO()
with tarfile.open(fileobj=data,mode='w:gz') as t:
 for n in ['results/'+project,project+'-'+job+'.log',project+'-'+job+'.err',project+'-accounting.txt','submissions/baseline-'+project+'.lock']:
  if (root/n).exists():t.add(root/n,arcname=n)
sys.stdout.buffer.write(data.getvalue())
''',seconds=60)
    inventory={}
    with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as t:
        for m in t.getmembers():
            n=PurePosixPath(m.name);assert not n.is_absolute() and '..' not in n.parts
            if m.isdir():continue
            assert m.isfile();data=t.extractfile(m).read();save(ROOT/m.name,data);inventory[m.name]=sha(data)
    save(ROOT/(project+'-transfer.json'),json.dumps(dict(files=inventory,compressed_bytes=len(raw)),indent=2).encode());print(json.dumps(dict(files=len(inventory),compressed_bytes=len(raw))))

if __name__=='__main__':
    action=sys.argv[1];assert action in {'stage','preflight','submit','status','fetch'}
    if action in {'stage','preflight'}:globals()[action]()
    else:globals()[action](sys.argv[2])
