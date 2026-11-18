"""Exclusive verifier-only stages; no paid runner, SDK or credential handling."""
import datetime

import hashlib

import io

import json

import re

import shutil

import stat

from pathlib import Path,PurePosixPath

import shlex

import subprocess

import sys

import tarfile

import common as c

from capture import write

def submit(stage):
    c.require(stage in STAGES,'Unknown verifier stage');c.validate_package();c.aggregate_budget(stage)
    sub=c.ROOT/'submissions';sub.mkdir(exist_ok=True)
    c.require(not list(sub.glob(stage+'.*')),'Existing submission/intention: inspect, never resubmit')
    write(sub/(stage+'.intent.json'),dict(stage=stage,model_calls=0,
        utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),runtime_sha256=c.sha(c.ROOT/'runtime-freeze.json')))
    code=CHECK+'stage='+repr(stage)+'\nscript='+repr(STAGES[stage])+'\nminutes='+str(c.STAGES[stage]['minutes'])+'\n'+r"""
import datetime,re,subprocess
sys.path.insert(0,str(root))
import common as runtime_common
aggregate_budget=runtime_common.aggregate_budget(stage)
assert aggregate_budget['cpus']==1 and aggregate_budget['job_minutes']==minutes
pre=json.loads((root/'remote-preflight-001.json').read_text())
assert pre['returncode']==0 and pre['runtime_sha256']==expected
sub=root/'submissions';sub.mkdir(exist_ok=True)
assert not list(sub.glob(stage+'.*')),'Existing submission state'
assert not (root/('verification-'+stage+'-001')).exists(),'Existing output'
queue=subprocess.check_output(['squeue','-u','sophiezeng','-h','-o','%i|%Z|%j|%T'],universal_newlines=True)
job_name={'dafny-vmc':'growth-controls-dafny','vest':'growth-controls-vest'}[stage]
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
       prior_queue=queue,runtime_sha256=expected,model_calls=0,no_requeue=True,aggregate_budget=aggregate_budget)
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

# An archive is final even when the native command failed. Only these explicit
# terminal Slurm base states permit it; live, requeue/held and unknown states do not.
TERMINAL_STATES=frozenset(('BOOT_FAIL','CANCELLED','COMPLETED','DEADLINE','FAILED',
                          'NODE_FAIL','OUT_OF_MEMORY','PREEMPTED','REVOKED','TIMEOUT'))
ACCOUNTING_FIELDS=('JobID','State','Elapsed','ElapsedRaw','ExitCode','AllocCPUS',
                   'TotalCPU','CPUTimeRAW','MaxRSS','NodeList')

def terminal_accounting(accounting,job):
    """Require one exact parent and terminal states for every returned step.

    A trailing '+' is Slurm's display-truncation marker; it is removable only
    when the remaining complete base state is known. The normal CANCELLED
    'by <numeric uid>' suffix is descriptive. An abbreviated base such as
    'OUT_OF_ME+' remains unknown and is rejected, never guessed.
    """
    c.require(isinstance(job,str) and re.fullmatch(r'[1-9][0-9]*',job),'Invalid parent JobID')
    c.require(isinstance(accounting,str),'Accounting must be decoded text')
    lines=[line for line in accounting.splitlines() if line.strip()]
    c.require(lines and tuple(x.strip() for x in lines[0].split('|'))==ACCOUNTING_FIELDS,
              'Unexpected accounting header')
    rows=[];seen=set();ignored=[]
    for line in lines[1:]:
        values=[x.strip() for x in line.split('|')]
        c.require(len(values)==len(ACCOUNTING_FIELDS),'Malformed accounting row')
        row=dict(zip(ACCOUNTING_FIELDS,values));ident=row['JobID']
        c.require(bool(ident),'Missing accounting JobID')
        if ident!=job and not ident.startswith(job+'.'):
            ignored.append(ident);continue
        if ident!=job:
            c.require(re.fullmatch(re.escape(job)+r'\.[A-Za-z0-9_-]+',ident),
                      'Malformed relevant step JobID')
        c.require(ident not in seen,'Duplicate parent or step accounting row')
        seen.add(ident);state=row['State']
        if state.endswith('+'):state=state[:-1].rstrip()
        match=re.fullmatch(r'([A-Z_]+)(?: by ([0-9]+))?',state)
        c.require(match is not None and (match.group(2) is None or match.group(1)=='CANCELLED'),
                  'Unknown accounting state syntax for '+ident)
        base=match.group(1)
        c.require(base in TERMINAL_STATES,'Nonterminal or unknown accounting state for '+ident+': '+row['State'])
        rows.append(dict(job_id=ident,state=row['State'],normalized_state=base,
                         kind='parent' if ident==job else 'step'))
    c.require(sum(row['job_id']==job for row in rows)==1,'Missing exact parent accounting row')
    return dict(parent_job_id=job,rows=rows,ignored_job_ids=ignored,all_relevant_rows_terminal=True,
                accounting_sha256=hashlib.sha256(accounting.encode()).hexdigest())

def transfer_inventory(root,stage,job,accounting,terminal_review):
    """Read-only estimate, rejecting links/special files and binding exact bytes."""
    c.require(stage in STAGES,'Unknown verifier stage')
    names=['verification-'+stage+'-001','submissions/'+stage+'.lock']
    c.require((root/names[0]).is_dir() and (root/names[1]).is_file(),'Missing transfer evidence')
    names+=sorted(p.name for p in root.glob(stage+'-'+job+'.*'))
    inventory={}
    def visit(path):
        mode=path.lstat().st_mode
        c.require(not stat.S_ISLNK(mode),'Symlink in transfer evidence')
        if stat.S_ISDIR(mode):
            for child in sorted(path.iterdir()):visit(child)
        else:
            c.require(stat.S_ISREG(mode),'Nonregular transfer evidence')
            data=path.read_bytes();inventory[path.relative_to(root).as_posix()]=dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
    for name in names:visit(root/name)
    virtual={'accounting-'+stage+'.txt':accounting.encode(),
             'accounting-'+stage+'-review.json':json.dumps(terminal_review,indent=2,sort_keys=True).encode()}
    for name,data in virtual.items():
        c.require(not(root/name).exists(),'Accounting/archive already created: inspect, never refetch')
        inventory[name]=dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
    return dict(source_bytes=sum(v['bytes'] for v in inventory.values()),regular_files=len(inventory),
                inventory_sha256=hashlib.sha256(json.dumps(inventory,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
                names=names+sorted(virtual),job_id=job,stage=stage)

def require_fetch_space(estimate,destination):
    size=estimate['source_bytes'];count=estimate['regular_files']
    c.require(type(size) is int and size>=0 and type(count) is int and count>0,'Invalid transfer size estimate')
    # Extraction needs the uncompressed bytes. Retain room for filesystem/receipt
    # overhead and unrelated concurrent writes; there is no partial-fetch recovery.
    headroom=max(64*1024*1024,(size+3)//4)
    available=shutil.disk_usage(destination).free;needed=size+headroom
    c.require(available>=needed,'Insufficient local disk space before fetch: need '+str(needed)+' bytes, free '+str(available)+'; neither endpoint was changed')
    return dict(source_bytes=size,headroom_bytes=headroom,required_free_bytes=needed,observed_free_bytes=available)

CHECK="""import hashlib,json,sys
expected=EXPECTED_RUNTIME
assert hashlib.sha256((root/'runtime-freeze.json').read_bytes()).hexdigest()==expected
for n,h in json.loads((root/'runtime-freeze.json').read_text())['files'].items():
 assert hashlib.sha256((root/n).read_bytes()).hexdigest()==h,n
"""

def remote(code,data=None,seconds=45):
    prefix="from pathlib import Path\nroot=Path.home()/'formal-disco/outputs/real-repository-growth-001/controls-001'\n"
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
    c.require(stage in STAGES,'Unknown verifier stage')
    job=c.read(c.ROOT/'submissions'/(stage+'.json'))['job_id']
    raw=remote('job='+repr(job)+'\nstage='+repr(stage)+'\n'+'''import subprocess,json
r=dict(accounting=subprocess.check_output(['sacct','-j',job,'--format=JobID,State,Elapsed,ExitCode,NodeList','-P'],universal_newlines=True))
folder=root/('verification-'+stage+'-001')
r['completed_records']=len(list(folder.glob('*/observation.json')))
print(json.dumps(r))
''');print(raw.decode())

def fetch(stage):
    c.require(stage in STAGES,'Unknown verifier stage')
    c.require(not (c.ROOT/('transfer-'+stage+'.json')).exists(),'Already fetched')
    job=c.read(c.ROOT/'submissions'/(stage+'.json'))['job_id']
    inspect=CHECK+'job='+repr(job)+'\nstage='+repr(stage)+'\n'+'''import subprocess,json,io,tarfile,sys
sys.path.insert(0,str(root))
from ops import terminal_accounting,transfer_inventory
accounting=subprocess.check_output(['sacct','-j',job,'--format=JobID%40,State%80,Elapsed,ElapsedRaw,ExitCode,AllocCPUS,TotalCPU,CPUTimeRAW,MaxRSS,NodeList','-P'],universal_newlines=True)
terminal_review=terminal_accounting(accounting,job)
inventory=transfer_inventory(root,stage,job,accounting,terminal_review)
'''
    estimate=json.loads(remote(inspect+'print(json.dumps(inventory))\n',seconds=60))
    c.require(estimate['stage']==stage and estimate['job_id']==job,'Transfer estimate identity differs')
    disk=require_fetch_space(estimate,c.ROOT)
    raw=remote(inspect+'assert inventory=='+repr(estimate)+',"Transfer evidence changed after size estimate"\n'+'''
with (root/('accounting-'+stage+'.txt')).open('x') as f:f.write(accounting)
with (root/('accounting-'+stage+'-review.json')).open('x') as f:json.dump(terminal_review,f,indent=2,sort_keys=True)
b=io.BytesIO()
with tarfile.open(fileobj=b,mode='w:gz') as t:
 for n in inventory['names']:t.add(root/n,arcname=n)
sys.stdout.buffer.write(b.getvalue())
''',seconds=60)
    inv={};sizes={}
    with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as t:
        for m in t.getmembers():
            n=PurePosixPath(m.name);c.require(not n.is_absolute() and '..' not in n.parts,'Unsafe archive path')
            if m.isdir():continue
            c.require(m.isfile() and str(n) not in inv,'Nonregular or duplicate artifact')
            c.require(not(c.ROOT/n).exists(),'Local extraction destination already exists')
            data=t.extractfile(m).read();inv[str(n)]=hashlib.sha256(data).hexdigest();sizes[str(n)]=dict(bytes=len(data),sha256=inv[str(n)])
        observed=hashlib.sha256(json.dumps(sizes,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        c.require(observed==estimate['inventory_sha256'] and sum(v['bytes'] for v in sizes.values())==estimate['source_bytes'] and len(sizes)==estimate['regular_files'],'Archive differs from read-only transfer estimate')
        # Check again immediately before extraction, retaining the same headroom.
        require_fetch_space(estimate,c.ROOT)
        for m in t.getmembers():
            if m.isfile():save(c.ROOT/m.name,t.extractfile(m).read())
    write(c.ROOT/('transfer-'+stage+'.json'),dict(files=inv,compressed_bytes=len(raw),archive_sha256=hashlib.sha256(raw).hexdigest(),job_id=job,
                                               read_only_estimate=estimate,pre_fetch_disk_check=disk))
    print(json.dumps(dict(files=len(inv),compressed_bytes=len(raw),job_id=job)))

if __name__=='__main__':
    action=sys.argv[1];c.require(action in ('stage','preflight','submit','status','fetch'),'Unknown operation')
    if action in ('submit','status','fetch'):c.require(len(sys.argv)==3 and sys.argv[2] in STAGES,'Choose verifier stage')
    globals()[action](*sys.argv[2:])
