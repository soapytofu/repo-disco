"""Bounded, exclusive SSH staging/submission/archive for verifier qualification."""
import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import shlex
import subprocess
import tarfile

ROOT=Path(__file__).resolve().parent
PACKAGE=ROOT.parent
SOCKET=Path.home()/'.ssh/repodisco-codex-21.sock'
HOST='sophiezeng@login.rc.fas.harvard.edu'
PYTHON='/n/home13/sophiezeng/.conda/envs/repodisco/bin/python'


def write(path,raw):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as stream:stream.write(raw)


def encode(obj):return (json.dumps(obj,indent=2,sort_keys=True)+'\n').encode()
def sha(raw):return hashlib.sha256(raw).hexdigest()


def identity(project):
    assert re.fullmatch(r'[a-z][a-z0-9-]{0,40}',project)
    path=ROOT/'freezes'/f'{project}.json'
    freeze=json.loads(path.read_bytes())
    for name,digest in freeze['files'].items():
        p=PurePosixPath(name)
        assert not p.is_absolute() and '..' not in p.parts
        source=PACKAGE/name
        assert not source.is_symlink() and sha(source.read_bytes())==digest,name
    return path,freeze


def remote(project,program,data=None,seconds=45):
    identity(project)
    prefix='from pathlib import Path\nEXPECTED_FREEZE='+repr(sha((ROOT/'freezes'/f'{project}.json').read_bytes()))+'\nroot=Path.home()/'+repr('formal-disco/outputs/dafny-real-library-growth-001/qualification-005/'+project)+'\n'
    argv=['ssh','-S',str(SOCKET),'-o','BatchMode=yes','-o','ConnectTimeout=10','-o','ProxyCommand=false',HOST]
    command=' '.join(shlex.quote(x) for x in [PYTHON,'-B','-c',prefix+program])
    p=subprocess.run(argv+[command],input=data,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=seconds)
    if p.returncode:raise RuntimeError(p.stderr.decode(errors='replace'))
    return p.stdout


CHECK='''import hashlib,json
freeze_bytes=(root/'qualification-005/freezes/PROJECT.json').read_bytes()
assert hashlib.sha256(freeze_bytes).hexdigest()==EXPECTED_FREEZE,'Remote freeze differs from authoritative local pin'
freeze=json.loads(freeze_bytes)
for name,digest in freeze['files'].items():
 p=root/name
 assert p.is_file() and not p.is_symlink() and hashlib.sha256(p.read_bytes()).hexdigest()==digest,name
'''


def inspect(project):
    raw=remote(project,'''import subprocess,json
q=subprocess.run(['squeue','-u','sophiezeng','-h','-o','%i|%j|%T|%Z'],capture_output=True,text=True,timeout=15)
print(json.dumps(dict(root=str(root),exists=root.exists(),files=[p.name for p in root.iterdir()] if root.exists() else [],queue=q.stdout)))
''')
    print(raw.decode())


def stage(project):
    freeze_path,freeze=identity(project)
    assert not (ROOT/'stages'/f'{project}.intent.json').exists()
    payload=io.BytesIO()
    with tarfile.open(fileobj=payload,mode='w:gz') as tar:
        for name in sorted(freeze['files']):tar.add(PACKAGE/name,arcname=name,recursive=False)
        tar.add(freeze_path,arcname='qualification-005/freezes/'+project+'.json',recursive=False)
    write(ROOT/'stages'/f'{project}.intent.json',encode(dict(freeze_sha256=sha(freeze_path.read_bytes()),native_calls=0,model_calls=0)))
    code='''import io,tarfile,sys,json
from pathlib import PurePosixPath
assert not root.exists(),'Existing remote stage: inspect; no retry'
with tarfile.open(fileobj=io.BytesIO(sys.stdin.buffer.read()),mode='r:gz') as tar:
 members=tar.getmembers();names=set()
 for m in members:
  p=PurePosixPath(m.name)
  assert m.isfile() and not p.is_absolute() and '..' not in p.parts and m.name not in names
  names.add(m.name)
 root.mkdir(parents=True)
 for m in members:
  p=root/m.name;p.parent.mkdir(parents=True,exist_ok=True)
  with p.open('xb') as f:f.write(tar.extractfile(m).read())
'''+CHECK.replace('PROJECT',project)+'''print(json.dumps(dict(root=str(root),files=len(freeze['files']),stage_complete=True)))
'''
    raw=remote(project,code,payload.getvalue(),180)
    write(ROOT/'stages'/f'{project}.json',raw);print(raw.decode())


def preflight(project):
    code=CHECK.replace('PROJECT',project)+'''import subprocess,json
log=root/'qualification-005/preflight.log'
assert not log.exists()
p=subprocess.run(['PYTHON','-B','-m','unittest','discover','-s',str(root/'qualification-005'),'-p','test_*.py','-v'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=45)
with log.open('xb') as f:f.write(p.stdout)
print(json.dumps(dict(exit_code=p.returncode,stdout=p.stdout.decode(),native_calls=0,model_calls=0)))
'''.replace('PYTHON',PYTHON)
    raw=remote(project,code,seconds=45)
    write(ROOT/'preflight'/f'{project}.json',raw)
    assert json.loads(raw)['exit_code']==0
    print(raw.decode())


def submit(project):
    assert json.loads((ROOT/'preflight'/f'{project}.json').read_bytes())['exit_code']==0
    write(ROOT/'submissions'/f'{project}.intent.json',encode(dict(project=project,no_retry=True)))
    code=CHECK.replace('PROJECT',project)+'''import subprocess,json
assert not (root/'submission.intent.json').exists() and not (root/'qualification-005/output-PROJECT').exists()
q=subprocess.run(['squeue','-u','sophiezeng','-h','-o','%i|%j|%Z'],capture_output=True,text=True,timeout=15);assert q.returncode==0
assert 'libq005-PROJECT' not in q.stdout and str(root) not in q.stdout
p=subprocess.run(['scontrol','show','partition','test'],capture_output=True,text=True,timeout=15)
assert p.returncode==0 and 'PreemptMode=OFF' in p.stdout and 'State=UP' in p.stdout and 'MaxTime=12:00:00' in p.stdout
(root/'partition-before-submit.txt').write_text(p.stdout)
with (root/'submission.intent.json').open('x') as f:json.dump(dict(project='PROJECT',no_retry=True),f)
command=['sbatch','--parsable','--export=ALL,REPODISCO_FREEZE_SHA='+EXPECTED_FREEZE+',REPODISCO_EXECUTION_ROOT='+str(root),'--job-name=libq005-PROJECT','--chdir='+str(root),str(root/'qualification-005/run.sbatch'),'PROJECT']
s=subprocess.run(command,cwd=root,capture_output=True,text=True,timeout=30)
record=dict(command=command,exit_code=s.returncode,stdout=s.stdout,stderr=s.stderr,partition=p.stdout)
with (root/'submission.json').open('x') as f:json.dump(record,f,indent=2)
print(json.dumps(record))
'''.replace('PROJECT',project)
    raw=remote(project,code,seconds=60);write(ROOT/'submissions'/f'{project}.json',raw)
    obj=json.loads(raw);assert obj['exit_code']==0
    assert re.fullmatch(r'[0-9]+(?:;[^\s]+)?\n?',obj['stdout'])
    print(raw.decode())


def status(project):
    job=json.loads((ROOT/'submissions'/f'{project}.json').read_bytes())['stdout'].strip().split(';')[0]
    assert job.isdigit()
    code='''import subprocess,json
job=JOB
p=subprocess.run(['sacct','-j',job,'-n','-P','--format=JobID,State,Elapsed,ExitCode,AllocCPUS,TotalCPU,MaxRSS,NodeList'],capture_output=True,text=True,timeout=20)
logs={p.name:p.read_text(errors='replace')[-10000:] for p in root.glob('qualification-'+job+'.*')}
print(json.dumps(dict(accounting=p.stdout,logs=logs)))
'''.replace('JOB',repr(job))
    raw=remote(project,code,seconds=35);print(raw.decode())


def fetch(project):
    job=json.loads((ROOT/'submissions'/f'{project}.json').read_bytes())['stdout'].strip().split(';')[0]
    assert job.isdigit()
    destination=ROOT/('retrieved-'+project)
    assert not destination.exists()
    code='''import subprocess,tarfile,io,sys
job=JOB
p=subprocess.run(['sacct','-j',job,'-P','--format=JobID,State%40,Elapsed,ExitCode,AllocCPUS,TotalCPU,MaxRSS,NodeList'],capture_output=True,text=True,timeout=20)
assert p.returncode==0
rows=[x.split('|') for x in p.stdout.splitlines()[1:] if x.strip()]
assert sum(x[0]==job for x in rows)==1
terminal={'COMPLETED','FAILED','CANCELLED','TIMEOUT','OUT_OF_MEMORY','NODE_FAIL','PREEMPTED','BOOT_FAIL','DEADLINE','REVOKED'}
relevant=[x for x in rows if x[0]==job or x[0].startswith(job+'.')]
assert len({x[0] for x in relevant})==len(relevant)
assert all(x[1].split()[0].rstrip('+') in terminal for x in relevant)
assert not (root/'accounting.txt').exists()
with (root/'accounting.txt').open('x') as f:f.write(p.stdout)
buf=io.BytesIO()
with tarfile.open(fileobj=buf,mode='w:gz') as tar:
 for path in sorted(root.rglob('*')):
  assert not path.is_symlink(),str(path)
  if path.is_file():tar.add(path,arcname=path.relative_to(root).as_posix(),recursive=False)
sys.stdout.buffer.write(buf.getvalue())
'''.replace('JOB',repr(job))
    raw=remote(project,code,seconds=240)
    archive=ROOT/('transfer-'+project+'.tar.gz');write(archive,raw)
    with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as tar:
        names=set();members=tar.getmembers()
        for m in members:
            p=PurePosixPath(m.name)
            assert m.isfile() and not p.is_absolute() and '..' not in p.parts and m.name not in names
            names.add(m.name)
        destination.mkdir()
        for m in members:write(destination/m.name,tar.extractfile(m).read())
    inventory={p.relative_to(destination).as_posix():sha(p.read_bytes()) for p in destination.rglob('*') if p.is_file()}
    write(ROOT/('transfer-'+project+'.json'),encode(dict(archive_sha256=sha(raw),files=inventory)))
    print(json.dumps(dict(project=project,files=len(inventory),archive_bytes=len(raw))))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['inspect','stage','preflight','submit','status','fetch']);p.add_argument('project')
    a=p.parse_args();globals()[a.action](a.project)
