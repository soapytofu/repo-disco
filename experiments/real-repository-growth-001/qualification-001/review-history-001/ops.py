"""Exclusive verifier-only stages; no paid runner, SDK or credential handling."""
import datetime

import hashlib

import io

import json

from pathlib import Path,PurePosixPath

import shlex

import subprocess

import sys

import tarfile

import common as c

from capture import write

def submit(stage):
    c.require(stage in STAGES,'Unknown verifier stage');c.validate_package()
    sub=c.ROOT/'submissions';sub.mkdir(exist_ok=True)
    c.require(not list(sub.glob(stage+'.*')),'Existing submission/intention: inspect, never resubmit')
    write(sub/(stage+'.intent.json'),dict(stage=stage,model_calls=0,
        utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),runtime_sha256=c.sha(c.ROOT/'runtime-freeze.json')))
    code=CHECK+'stage='+repr(stage)+'\nscript='+repr(STAGES[stage])+'\nminutes='+str(c.STAGES[stage]['minutes'])+'\n'+r"""
import datetime,re,subprocess
pre=json.loads((root/'remote-preflight-001.json').read_text())
assert pre['returncode']==0 and pre['runtime_sha256']==expected
sub=root/'submissions';sub.mkdir(exist_ok=True)
assert not list(sub.glob(stage+'.*')),'Existing submission state'
assert not (root/('verification-'+stage+'-001')).exists(),'Existing output'
queue=subprocess.check_output(['squeue','-u','sophiezeng','-h','-o','%i|%Z|%j|%T'],universal_newlines=True)
job_name={'dafny-vmc':'growth-reference-dafny','vest':'growth-reference-vest'}[stage]
assert not any(str(root) in line and job_name in line for line in queue.splitlines()),'Matching job queued'
observed={};chosen=None
for partition in ['test','shared']:
 text=subprocess.check_output(['scontrol','show','partition',partition],universal_newlines=True);observed[partition]=text
 if 'PreemptMode=OFF' not in text or 'State=UP' not in text:continue
 maximum=re.search(r'\bMaxTime=(\S+)',text).group(1)
 if maximum=='UNLIMITED':allowed=True
 else:
  days,clock=(maximum.split('-',1) if '-' in maximum else ('0',maximum));h,m,s=map(int,clock.split(':'))
  allowed=(int(days)*1440+h*60+m+s/60)>=minutes
 if allowed:chosen=partition;break
assert chosen,'No verified nonpreemptible suitable partition'
r=dict(stage=stage,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),partitions=observed,partition=chosen,
       prior_queue=queue,runtime_sha256=expected,model_calls=0,no_requeue=True)
with (sub/(stage+'.lock')).open('x') as f:json.dump(r,f)
try:
 p=subprocess.run(['sbatch','--parsable','--partition='+chosen,script],cwd=str(root),
                  stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=25)
 r.update(returncode=p.returncode,stdout=p.stdout,stderr=p.stderr)
 if p.returncode==0:
  job=p.stdout.strip().split(';')[0];assert job.isdigit();r['job_id']=job
except subprocess.TimeoutExpired:r['ambiguous_submission']=True
with (sub/(stage+'.json')).open('x') as f:json.dump(r,f,indent=2)
print(json.dumps(r))
"""
    try:raw=remote(code,seconds=60)
    except BaseException as e:
        write(sub/(stage+'.transport-failure.json'),dict(type=type(e).__name__,submission_outcome_requires_read_only_review=True))
        raise
    save(sub/(stage+'.json'),raw);record=json.loads(raw)
    print(json.dumps({k:v for k,v in record.items() if k not in ('partitions','prior_queue')},indent=2))

SSH=['ssh','-S',str(Path.home()/'.ssh/repodisco-codex-21.sock'),'-o','BatchMode=yes','-o','ConnectTimeout=8',
     '-o','ProxyCommand=false','sophiezeng@login.rc.fas.harvard.edu']

STAGES={'dafny-vmc':'verify-dafny-vmc.sbatch','vest':'verify-vest.sbatch'}

CHECK="""import hashlib,json,sys
expected=EXPECTED_RUNTIME
assert hashlib.sha256((root/'runtime-freeze.json').read_bytes()).hexdigest()==expected
for n,h in json.loads((root/'runtime-freeze.json').read_text())['files'].items():
 assert hashlib.sha256((root/n).read_bytes()).hexdigest()==h,n
"""

def remote(code,data=None,seconds=45):
    prefix="from pathlib import Path\nroot=Path.home()/'formal-disco/outputs/real-repository-growth-001/qualification-001'\n"
    code=code.replace('EXPECTED_RUNTIME',repr(c.sha(c.ROOT/'runtime-freeze.json')))
    p=subprocess.run(SSH+['python3 -c '+shlex.quote(prefix+code)],input=data,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=seconds)
    if p.stderr:print(p.stderr.decode(),file=sys.stderr)
    p.check_returncode();return p.stdout

def save(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as f:f.write(data)

def stage():
    c.validate_package();c.require(not (c.ROOT/'stage-001.json').exists(),'Already staged')
    pins=c.read(c.ROOT/'runtime-freeze.json')['files'];b=io.BytesIO()
    with tarfile.open(fileobj=b,mode='w:gz') as t:
        for n in sorted(set(pins)|{'runtime-freeze.json'}):t.add(c.ROOT/n,arcname=n,recursive=False)
    raw=remote('''import io,tarfile,sys,json
from pathlib import PurePosixPath
assert not root.exists(),'Destination already exists: inspect; do not restage'
root.mkdir(parents=True)
with tarfile.open(fileobj=io.BytesIO(sys.stdin.buffer.read()),mode='r:gz') as t:
 for m in t.getmembers():
  n=PurePosixPath(m.name);assert m.isfile() and not n.is_absolute() and '..' not in n.parts
  dest=root/n;dest.parent.mkdir(parents=True,exist_ok=True)
  with dest.open('xb') as f:f.write(t.extractfile(m).read())
'''+CHECK+'''
print(json.dumps(dict(root=str(root),runtime_sha256=expected,model_calls=0,verifier_calls=0)))
''',b.getvalue(),60)
    save(c.ROOT/'stage-001.json',raw);print(raw.decode())

def preflight():
    c.require(not (c.ROOT/'remote-preflight-001.json').exists(),'Preflight already recorded')
    raw=remote(CHECK+'''import subprocess
assert not (root/'remote-preflight-001.json').exists(),'Preflight already recorded'
p=subprocess.run([str(Path.home()/'.conda/envs/repodisco/bin/python'),'-B','preflight.py'],cwd=str(root),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=55)
r=json.loads(p.stdout.decode());r['driver_stderr']=p.stderr.decode();assert r['returncode']==p.returncode
with (root/'remote-preflight-001.json').open('x') as f:json.dump(r,f,indent=2)
print(json.dumps(r))
''',seconds=65)
    save(c.ROOT/'remote-preflight-001.json',raw);r=json.loads(raw);print(r['log']);c.require(r['returncode']==0,'Remote offline preflight failed')

def status(stage):
    job=c.read(c.ROOT/'submissions'/(stage+'.json'))['job_id']
    raw=remote('job='+repr(job)+'\nstage='+repr(stage)+'\n'+'''import subprocess,json
r=dict(accounting=subprocess.check_output(['sacct','-j',job,'--format=JobID,State,Elapsed,ExitCode,NodeList','-P'],universal_newlines=True))
folder=root/('verification-'+stage+'-001')
r['completed_records']=len(list(folder.glob('*/observation.json')))
print(json.dumps(r))
''');print(raw.decode())

def fetch(stage):
    c.require(not (c.ROOT/('transfer-'+stage+'.json')).exists(),'Already fetched')
    job=c.read(c.ROOT/'submissions'/(stage+'.json'))['job_id']
    raw=remote('job='+repr(job)+'\nstage='+repr(stage)+'\n'+'''import subprocess,json,io,tarfile,sys
accounting=subprocess.check_output(['sacct','-j',job,'--format=JobID,State,Elapsed,ElapsedRaw,ExitCode,AllocCPUS,TotalCPU,CPUTimeRAW,MaxRSS,NodeList','-P'],universal_newlines=True)
assert job+'|' in accounting and not any(s in accounting for s in ['RUNNING','PENDING','COMPLETING','CONFIGURING'])
with (root/('accounting-'+stage+'.txt')).open('x') as f:f.write(accounting)
names=[('verification-'+stage+'-001'),'accounting-'+stage+'.txt','submissions/'+stage+'.lock']

names += [p.name for p in root.glob(stage+'-'+job+'.*')]
b=io.BytesIO()
with tarfile.open(fileobj=b,mode='w:gz') as t:
 for n in names:
  if (root/n).exists():t.add(root/n,arcname=n)
sys.stdout.buffer.write(b.getvalue())
''',seconds=60)
    inv={}
    with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as t:
        for m in t.getmembers():
            n=PurePosixPath(m.name);c.require(not n.is_absolute() and '..' not in n.parts,'Unsafe archive path')
            if m.isdir():continue
            c.require(m.isfile(),'Nonregular artifact');data=t.extractfile(m).read();save(c.ROOT/n,data);inv[str(n)]=hashlib.sha256(data).hexdigest()
    write(c.ROOT/('transfer-'+stage+'.json'),dict(files=inv,compressed_bytes=len(raw),archive_sha256=hashlib.sha256(raw).hexdigest(),job_id=job))
    print(json.dumps(dict(files=len(inv),compressed_bytes=len(raw),job_id=job)))

if __name__=='__main__':
    action=sys.argv[1];c.require(action in ('stage','preflight','submit','status','fetch'),'Unknown operation')
    if action in ('submit','status','fetch'):c.require(len(sys.argv)==3 and sys.argv[2] in STAGES,'Choose verifier stage')
    globals()[action](*sys.argv[2:])
