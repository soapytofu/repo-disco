"""Exclusive verifier-only operations; all remote programs use stdin."""
import argparse
import base64
import hashlib
import inspect as python_inspect
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import shutil
import stat
import subprocess
import tarfile
import time

ROOT=Path(__file__).resolve().parent
PACKAGE=ROOT.parent
SOCKET=Path.home()/".ssh/repodisco-codex-21.sock"
HOST="sophiezeng@login.rc.fas.harvard.edu"
PYTHON="/n/home13/sophiezeng/.conda/envs/repodisco/bin/python"
REMOTE_BASE="/n/home13/sophiezeng/formal-disco/outputs/dafny-real-library-growth-002/qualification-005"
MAX_ARCHIVE_BYTES=2*1024**3
MAX_STAGE_BYTES=8*1024**2
MAX_PROGRAM_BYTES=16*1024**2
JOB_SECONDS=3600
ACCOUNTING_FIELDS=("JobID","State","Elapsed","ElapsedRaw","ExitCode","AllocCPUS",
                   "TotalCPU","CPUTimeRAW","MaxRSS","NodeList")
TERMINAL_STATES=frozenset(("BOOT_FAIL","CANCELLED","COMPLETED","DEADLINE","FAILED",
                          "NODE_FAIL","OUT_OF_MEMORY","PREEMPTED","REVOKED","TIMEOUT"))
TIMEOUTS={"inspect":45,"stage":180,"preflight":120,"submit":90,"status":45,"estimate":90,"fetch":240}

def require(ok,message):
    if not ok:raise ValueError(message)


def sha(raw):return hashlib.sha256(raw).hexdigest()


def canonical(value):return json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()


def read(path):return json.loads(Path(path).read_bytes())


def write(path,raw):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("xb") as stream:
        stream.write(raw);stream.flush();os.fsync(stream.fileno())


def save(path,value):write(path,canonical(value)+b"\n")


def safe_name(name):
    return (isinstance(name,str) and name and not PurePosixPath(name).is_absolute()
            and "\\" not in name and all(p not in {"",".",".."} for p in name.split("/"))
            and all(32<=ord(c)<127 for c in name))


def canonical_location(value):
    path=Path(value)
    require(path.is_absolute() and str(path)==value and str(path.resolve())==value,"Noncanonical location")
    for parent in (path,*path.parents):require(not parent.is_symlink(),"Symlink in canonical location")
    return path


def regular_files(folder):
    folder=Path(folder);result={}
    require(folder.is_dir() and not folder.is_symlink(),"Nonregular evidence root")
    for path in sorted(folder.rglob("*")):
        mode=path.lstat().st_mode
        require(not stat.S_ISLNK(mode),"Symlink evidence cannot be archived")
        if stat.S_ISDIR(mode):continue
        require(stat.S_ISREG(mode),"Nonregular evidence")
        name=path.relative_to(folder).as_posix()
        require(safe_name(name),"Unsafe evidence name")
        result[name]=path.read_bytes()
    return result


def archive_members(raw):
    require(isinstance(raw,bytes) and len(raw)<=MAX_ARCHIVE_BYTES,"Transfer exceeds byte bound")
    members={}
    with tarfile.open(fileobj=io.BytesIO(raw),mode="r:gz") as archive:
        for member in archive.getmembers():
            require(member.isfile() and safe_name(member.name) and member.name not in members,
                    "Unsafe, nonregular or duplicate archive entry")
            require(0<=member.size<=MAX_ARCHIVE_BYTES
                    and sum(len(x) for x in members.values())+member.size<=MAX_ARCHIVE_BYTES,
                    "Expanded archive exceeds byte bound")
            data=archive.extractfile(member).read()
            require(len(data)==member.size,"Truncated archive member")
            members[member.name]=data
    require(members and not any(str(parent) in members for name in members
            for parent in PurePosixPath(name).parents),"Archive has file/directory path collision")
    return members


def make_archive(files):
    buffer=io.BytesIO()
    with tarfile.open(fileobj=buffer,mode="w:gz") as archive:
        for name,data in sorted(files.items()):
            require(safe_name(name) and isinstance(data,bytes),"Invalid archive input")
            info=tarfile.TarInfo(name);info.size=len(data);info.mode=0o600
            archive.addfile(info,io.BytesIO(data))
    return buffer.getvalue()


def terminal_accounting(accounting,job):
    require(isinstance(job,str) and re.fullmatch(r"[1-9][0-9]*",job),"Invalid exact parent JobID")
    lines=[line for line in accounting.splitlines() if line.strip()]
    require(lines and tuple(x.strip() for x in lines[0].split("|"))==ACCOUNTING_FIELDS,
            "Unexpected accounting header")
    rows=[];seen=set();ignored=[]
    for line in lines[1:]:
        values=[x.strip() for x in line.split("|")]
        require(len(values)==len(ACCOUNTING_FIELDS),"Malformed accounting row")
        row=dict(zip(ACCOUNTING_FIELDS,values));ident=row["JobID"]
        require(ident,"Missing accounting JobID")
        if ident!=job and not ident.startswith(job+"."):
            ignored.append(ident);continue
        require(ident==job or re.fullmatch(re.escape(job)+r"\.[A-Za-z0-9_-]+",ident),"Malformed relevant step")
        require(ident not in seen,"Duplicate parent or step");seen.add(ident)
        state=row["State"]
        if state.endswith("+"):state=state[:-1].rstrip()
        match=re.fullmatch(r"([A-Z_]+)(?: by ([0-9]+))?",state)
        require(match and (match.group(2) is None or match.group(1)=="CANCELLED"),"Unknown state syntax")
        require(match.group(1) in TERMINAL_STATES,"Nonterminal/unknown parent or step")
        rows.append(dict(job_id=ident,state=row["State"],normalized_state=match.group(1)))
    require(sum(r["job_id"]==job for r in rows)==1,"Missing exact parent accounting")
    return dict(parent_job_id=job,rows=rows,ignored_job_ids=ignored,all_relevant_rows_terminal=True,
                accounting_sha256=sha(accounting.encode()))


def settings(project):
    require(project=='stdlib', 'Only revised Stdlib references are dispatchable')
    return dict(project=project,root=REMOTE_BASE+'/'+project,
                job_name='g2q005-'+project,freeze='qualification-005/freezes/'+project+'.json')


def identity(project):
    from collect import REFERENCE_IDS, validate_config
    selected=settings(project)
    path=ROOT/'freezes'/f'{project}.json'
    frozen=read(path)
    require(frozen.get('schema')=='dafny-growth-reference-freeze-v1'
            and frozen.get('project')==project
            and frozen.get('reference_case_ids')==REFERENCE_IDS[project], 'Unreviewed dispatch freeze')
    required={'qualification-005/'+name for name in
              ('ops.py','collect.py','review.py','run.sbatch','native_scorer.py','tool-profiles.json','test_runtime.py')}
    required.add('qualification-005/configs/'+project+'.json')
    required.add('qualification-005/reference-metadata/'+project+'.json')
    required.update('qualification-005/inherited-profiles/'+name for name in
                    ('stdlib-stage0.json','stdlib-stage1.json'))
    require(required <= set(frozen['files']), 'Runtime omits an operational input')
    for name,digest in frozen['files'].items():
        require(safe_name(name), 'Unsafe runtime path')
        source=PACKAGE/name
        require(source.is_file() and not source.is_symlink() and sha(source.read_bytes())==digest,
                'Runtime input differs: '+name)
    config=validate_config(read(ROOT/'configs'/f'{project}.json'))
    for case in config['cases']:
        for name,digest in case['source_sha256'].items():
            require(frozen['files'].get(case['workspace_dir']+'/'+name)==digest,
                    'Reference source absent from freeze')
    return selected,path,frozen


def command(argv,seconds=20):
    result=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=seconds)
    require(result.returncode==0, 'Read-only cluster command failed: '+argv[0])
    return result.stdout.decode('utf-8')


def no_matching_queue(text,selected):
    for line in text.splitlines():
        if not line.strip():continue
        fields=line.split('|')
        require(len(fields)==4 and fields[0], 'Malformed queue listing')
        job,working,name,state=(x.strip() for x in fields)
        require(name!=selected['job_name'] and working!=selected['root']
                and not working.startswith(selected['root']+'/'), 'Matching job is queued')


def inspect_state(selected):
    root=canonical_location(selected['root'])
    output=root/Path(selected['freeze']).parent.parent/('output-'+selected['project'])
    queue=command(['squeue','-u','sophiezeng','-h','-o','%i|%Z|%j|%T'],15)
    return dict(root_exists=root.exists(),
        output_path=str(output),output_exists=output.exists(),
        submission_exists=any((root/name).exists() for name in ('submission.intent.json','submission.json')),
        fetch_exists=(root/'fetch.intent.json').exists(),queue=queue)


def fresh_state(state,selected,*,staging=False):
    no_matching_queue(state['queue'],selected)
    require(not state['output_exists'] and not state['submission_exists'] and not state['fetch_exists'],
            'Existing output/submission/archive intent; no retry')
    require(state['root_exists'] != staging, 'Unexpected remote staging state')


def verify_package(selected,digest,*,allow_drift=False):
    root=canonical_location(selected['root'])
    path=root/selected['freeze']
    require(path.is_file() and not path.is_symlink() and sha(path.read_bytes())==digest,
            'Authoritative remote runtime freeze differs')
    frozen=read(path);changed=[];missing=[]
    for name,expected in frozen['files'].items():
        require(safe_name(name), 'Unsafe frozen remote member')
        path=root/name
        require(not path.is_symlink(), 'Symlink frozen member')
        if not path.is_file():missing.append(name)
        elif sha(path.read_bytes())!=expected:changed.append(name)
    require(allow_drift or not changed and not missing, 'Remote runtime/source drift')
    return frozen,dict(changed=changed,missing=missing,unchanged=not changed and not missing)


def stage_remote(selected,digest,payload):
    require(isinstance(payload,bytes) and len(payload)<=MAX_STAGE_BYTES, 'Stage byte bound exceeded')
    fresh_state(inspect_state(selected),selected,staging=True)
    members=archive_members(payload)
    require(selected['freeze'] in members and sha(members[selected['freeze']])==digest,
            'Staged manifest identity differs')
    frozen=json.loads(members[selected['freeze']])
    require(set(members)==set(frozen['files'])|{selected['freeze']}, 'Unpinned stage member')
    require(all(sha(members[name])==expected for name,expected in frozen['files'].items()),
            'Staged source differs')
    root=Path(selected['root']);root.parent.mkdir(parents=True,exist_ok=True);root.mkdir()
    save(root/'stage.intent.json',dict(runtime_sha256=digest,no_retry=True,native_calls=0,model_calls=0))
    for name,data in members.items():write(root/name,data)
    verify_package(selected,digest)
    record=dict(runtime_sha256=digest,files=len(members),native_calls=0,model_calls=0,stage_complete=True)
    save(root/'stage-001.json',record)
    return record


def preflight_remote(selected,digest):
    verify_package(selected,digest);fresh_state(inspect_state(selected),selected)
    root=Path(selected['root'])
    require(not (root/'preflight.intent.json').exists() and not (root/'preflight-001.json').exists(),
            'Preflight already attempted')
    save(root/'preflight.intent.json',dict(runtime_sha256=digest,no_retry=True))
    argv=[PYTHON,'-B','-m','unittest','discover','-s',str(root/'qualification-005'),'-p','test_*.py','-v']
    started=time.monotonic()
    try:
        result=subprocess.run(argv,cwd=root,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=60)
        code,out,err,timed=result.returncode,result.stdout,result.stderr,False
    except subprocess.TimeoutExpired as error:
        code,out,err,timed=None,error.stdout or b'',error.stderr or b'',True
    write(root/'preflight.stdout.txt',out);write(root/'preflight.stderr.txt',err)
    record=dict(runtime_sha256=digest,argv=argv,exit_code=code,timeout=timed,
                elapsed_seconds=time.monotonic()-started,native_calls=0,model_calls=0)
    save(root/'preflight-001.json',record)
    return record


def check_partition(text):
    pairs=re.findall(r'(?:^|\s)([A-Za-z][A-Za-z0-9]*)=(\S+)',text)
    require(len({k for k,v in pairs})==len(pairs), 'Duplicate partition fields')
    fields=dict(pairs)
    require(fields.get('PartitionName')=='test' and fields.get('State')=='UP'
            and fields.get('PreemptMode')=='OFF', 'Need live UP/nonpreemptible test partition')
    maximum=fields.get('MaxTime','')
    if maximum!='UNLIMITED':
        match=re.fullmatch(r'(?:(\d+)-)?(\d+):(\d{2}):(\d{2})',maximum)
        require(match is not None, 'Unrecognized partition time limit')
        days,hours,minutes,seconds=(int(x or 0) for x in match.groups())
        require(minutes<60 and seconds<60 and ((days*24+hours)*60+minutes)*60+seconds>=JOB_SECONDS,
                'Partition cannot fit one-hour serial qualification')
    for key,minimum in (('MaxCPUsPerNode',1),('MaxMemPerNode',4096),('MaxMemPerCPU',4096)):
        value=fields.get(key,'UNLIMITED')
        require(value in {'UNLIMITED','0'} or value.isdigit() and int(value)>=minimum,
                'Partition resource bound is insufficient')


def submit_remote(selected,digest):
    verify_package(selected,digest);fresh_state(inspect_state(selected),selected)
    root=Path(selected['root']);pre=read(root/'preflight-001.json')
    require(pre['runtime_sha256']==digest and pre['exit_code']==0 and not pre['timeout'],
            'Successful exact fake-process preflight required')
    partition=command(['scontrol','show','partition','test'],15);check_partition(partition)
    write(root/'partition-before-submit.txt',partition.encode())
    save(root/'submission.intent.json',dict(runtime_sha256=digest,no_retry=True,maximum_submission_attempts=1))
    argv=['sbatch','--parsable','--partition=test','--nodes=1','--ntasks=1','--cpus-per-task=1',
          '--mem=4G','--time=01:00:00','--no-requeue','--job-name='+selected['job_name'],
          '--chdir='+str(root),'--export=ALL,REPODISCO_FREEZE_SHA='+digest+',REPODISCO_EXECUTION_ROOT='+str(root),
          str(root/'qualification-005/run.sbatch'),selected['project']]
    record=dict(runtime_sha256=digest,argv=argv)
    try:
        result=subprocess.run(argv,cwd=root,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30)
        record.update(exit_code=result.returncode,stdout=result.stdout.decode(errors='replace'),
                      stderr=result.stderr.decode(errors='replace'))
        match=re.fullmatch(r'([1-9][0-9]*)(?:;[A-Za-z0-9_.-]+)?\s*',record['stdout'])
        if result.returncode==0 and match:record['job_id']=match.group(1)
        elif result.returncode==0:record['ambiguous_submission']=True
    except BaseException as error:
        record.update(error_type=type(error).__name__,ambiguous_submission=True)
    save(root/'submission.json',record)
    return record


def accounting(job):
    require(isinstance(job,str) and re.fullmatch(r'[1-9][0-9]*',job), 'Invalid parent JobID')
    return command(['sacct','-j',job,'-P',
        '--format=JobID%40,State%80,Elapsed,ElapsedRaw,ExitCode,AllocCPUS,TotalCPU,CPUTimeRAW,MaxRSS,NodeList'],20)


def transfer_files(selected,digest,job):
    root=canonical_location(selected['root'])
    text=accounting(job);terminal=terminal_accounting(text,job)
    no_matching_queue(inspect_state(selected)['queue'],selected)
    frozen,integrity=verify_package(selected,digest,allow_drift=True)
    require(not (root/'fetch.intent.json').exists(), 'Final archive already claimed; no retry')
    require(read(root/'submission.json').get('job_id')==job, 'Remote submission identity differs')
    files=regular_files(root)
    require(not {'accounting.txt','accounting-review.json','runtime-integrity.json'} & set(files),
            'Conflicting accounting archive members')
    files['accounting.txt']=text.encode();files['accounting-review.json']=canonical(terminal)
    files['runtime-integrity.json']=canonical(integrity)
    inventory={name:dict(bytes=len(data),sha256=sha(data)) for name,data in sorted(files.items())}
    require(sum(len(data) for data in files.values())<=MAX_ARCHIVE_BYTES, 'Archive byte bound exceeded')
    return files,dict(project=selected['project'],job_id=job,source_bytes=sum(len(x) for x in files.values()),
        regular_files=len(files),inventory=inventory,inventory_sha256=sha(canonical(inventory)))


def fetch_remote(selected,digest,job,expected_inventory):
    files,inventory=transfer_files(selected,digest,job)
    require(inventory==expected_inventory, 'Terminal evidence changed since estimate')
    save(Path(selected['root'])/'fetch.intent.json',dict(job_id=job,
         inventory_sha256=inventory['inventory_sha256'],no_retry=True))
    return make_archive(files)


REMOTE_FUNCTIONS=(require,sha,canonical,read,write,save,safe_name,canonical_location,regular_files,
    archive_members,make_archive,terminal_accounting,command,no_matching_queue,inspect_state,
    fresh_state,verify_package,stage_remote,preflight_remote,check_partition,submit_remote,
    accounting,transfer_files,fetch_remote)


def remote_program(action,selected,digest,*,payload=None,job=None,inventory=None):
    require(action in TIMEOUTS, 'Unknown operation')
    require((action=='stage')==(payload is not None), 'Only stage takes a frozen package payload')
    require(payload is None or isinstance(payload,bytes) and len(payload)<=MAX_STAGE_BYTES,
            'Stage payload bound exceeded')
    constants=dict(MAX_ARCHIVE_BYTES=MAX_ARCHIVE_BYTES,MAX_STAGE_BYTES=MAX_STAGE_BYTES,
        ACCOUNTING_FIELDS=ACCOUNTING_FIELDS,TERMINAL_STATES=TERMINAL_STATES,PYTHON=PYTHON,
        JOB_SECONDS=JOB_SECONDS,SELECTED=selected,DIGEST=digest,JOB=job,INVENTORY=inventory,
        PAYLOAD=base64.b64encode(payload).decode() if payload is not None else None)
    code='import base64,hashlib,io,json,os,re,stat,subprocess,sys,tarfile,time\nfrom pathlib import Path,PurePosixPath\n'
    code+='\n'.join(name+'='+repr(value) for name,value in constants.items())+'\n'
    code+='\n'.join(python_inspect.getsource(function) for function in REMOTE_FUNCTIONS)
    endings={'inspect':'print(json.dumps(inspect_state(SELECTED)))',
        'stage':'print(json.dumps(stage_remote(SELECTED,DIGEST,base64.b64decode(PAYLOAD,validate=True))))',
        'preflight':'print(json.dumps(preflight_remote(SELECTED,DIGEST)))',
        'submit':'print(json.dumps(submit_remote(SELECTED,DIGEST)))',
        'status':'print(json.dumps(dict(job_id=JOB,accounting=accounting(JOB),state=inspect_state(SELECTED))))',
        'estimate':'print(json.dumps(transfer_files(SELECTED,DIGEST,JOB)[1]))',
        'fetch':'sys.stdout.buffer.write(fetch_remote(SELECTED,DIGEST,JOB,INVENTORY))'}
    return code+'\n'+endings[action]+'\n'


def remote(project,action,*,payload=None,job=None,inventory=None):
    selected,path,frozen=identity(project)
    program=remote_program(action,selected,sha(path.read_bytes()),payload=payload,job=job,inventory=inventory).encode()
    require(len(program)<=MAX_PROGRAM_BYTES, 'Remote program exceeds stdin byte bound')
    argv=['ssh','-S',str(SOCKET),'-o','ControlMaster=no','-o','BatchMode=yes','-o','ConnectTimeout=10',
          '-o','ProxyCommand=false','-o','NumberOfPasswordPrompts=0',HOST,
          ' '.join(shlex.quote(x) for x in [PYTHON,'-B','-'])]
    require(all(len(arg.encode())<4096 for arg in argv), 'Large command argument forbidden')
    result=subprocess.run(argv,input=program,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=TIMEOUTS[action])
    if result.returncode:
        raise RuntimeError('Bounded SSH failed: '+result.stderr.decode(errors='replace')[-4000:])
    return result.stdout


def local_fresh(project,action):
    if action=='stage':names=[f'stages/{project}.intent.json',f'stages/{project}.json']
    elif action=='preflight':names=[f'preflight/{project}.intent.json',f'preflight/{project}.json']
    elif action=='submit':names=[f'submissions/{project}.intent.json',f'submissions/{project}.json',
                                  f'submissions/{project}.transport-failure.json']
    elif action=='fetch':names=[f'fetch/{project}.intent.json',f'transfer-{project}.json',
                               f'transfer-{project}.tar.gz',f'retrieved-{project}']
    else:raise ValueError('Unknown local mutation')
    require(not any((ROOT/name).exists() for name in names), 'Existing local intent/evidence; no retry')


def stage(project):
    selected,path,frozen=identity(project);local_fresh(project,'stage')
    before=json.loads(remote(project,'inspect'));fresh_state(before,selected,staging=True)
    files={name:(PACKAGE/name).read_bytes() for name in frozen['files']}
    files[selected['freeze']]=path.read_bytes();payload=make_archive(files)
    require(len(payload)<=MAX_STAGE_BYTES, 'Frozen package too large')
    save(ROOT/'stages'/f'{project}.intent.json',dict(runtime_sha256=sha(path.read_bytes()),prior_state=before,no_retry=True))
    raw=remote(project,'stage',payload=payload)
    write(ROOT/'stages'/f'{project}.json',raw);print(raw.decode())


def preflight(project):
    selected,path,frozen=identity(project);local_fresh(project,'preflight')
    before=json.loads(remote(project,'inspect'));fresh_state(before,selected)
    save(ROOT/'preflight'/f'{project}.intent.json',dict(runtime_sha256=sha(path.read_bytes()),prior_state=before,no_retry=True))
    raw=remote(project,'preflight');write(ROOT/'preflight'/f'{project}.json',raw)
    result=json.loads(raw);print(raw.decode())
    require(result['exit_code']==0 and not result['timeout'], 'Fake-process/import preflight failed')


def submit(project):
    selected,path,frozen=identity(project);local_fresh(project,'submit')
    pre=read(ROOT/'preflight'/f'{project}.json')
    require(pre['runtime_sha256']==sha(path.read_bytes()) and pre['exit_code']==0 and not pre['timeout'],
            'Local exact preflight required')
    before=json.loads(remote(project,'inspect'));fresh_state(before,selected)
    save(ROOT/'submissions'/f'{project}.intent.json',dict(runtime_sha256=sha(path.read_bytes()),
        prior_state=before,no_retry=True,maximum_submission_attempts=1))
    try:raw=remote(project,'submit')
    except BaseException as error:
        save(ROOT/'submissions'/f'{project}.transport-failure.json',dict(error_type=type(error).__name__,
             ambiguous_submission=True,no_retry=True));raise
    write(ROOT/'submissions'/f'{project}.json',raw);print(raw.decode())
    result=json.loads(raw)
    require('job_id' in result and not result.get('ambiguous_submission'), 'Submission failed or ambiguous; no retry')


def submitted_job(project):
    record=read(ROOT/'submissions'/f'{project}.json');job=record.get('job_id')
    require(isinstance(job,str) and re.fullmatch(r'[1-9][0-9]*',job)
            and not record.get('ambiguous_submission'), 'No unambiguous submitted job')
    return job


def status(project):print(remote(project,'status',job=submitted_job(project)).decode())
def inspect_remote(project):print(remote(project,'inspect').decode())


def check_space(estimate,*,archive_saved=False):
    size=estimate['source_bytes']
    require(type(size) is int and 0<size<=MAX_ARCHIVE_BYTES, 'Invalid archive estimate')
    required=(1 if archive_saved else 2)*size+64*1024**2
    available=shutil.disk_usage(ROOT).free
    require(available>=required, 'Insufficient disk for archive and extraction')
    return dict(required_free_bytes=required,available_free_bytes=available)


def fetch(project):
    selected,path,frozen=identity(project);local_fresh(project,'fetch');job=submitted_job(project)
    estimate=json.loads(remote(project,'estimate',job=job))
    require(estimate['project']==project and estimate['job_id']==job, 'Archive identity differs')
    space=check_space(estimate)
    save(ROOT/'fetch'/f'{project}.intent.json',dict(job_id=job,
         inventory_sha256=estimate['inventory_sha256'],no_retry=True))
    raw=remote(project,'fetch',job=job,inventory=estimate)
    write(ROOT/f'transfer-{project}.tar.gz',raw)
    files=archive_members(raw)
    inventory={name:dict(bytes=len(data),sha256=sha(data)) for name,data in sorted(files.items())}
    require(inventory==estimate['inventory'] and sha(canonical(inventory))==estimate['inventory_sha256'],
            'Archive differs from terminal inventory')
    check_space(estimate,archive_saved=True)
    destination=ROOT/f'retrieved-{project}';destination.mkdir()
    for name,data in files.items():write(destination/name,data)
    save(ROOT/f'transfer-{project}.json',dict(project=project,job_id=job,archive_sha256=sha(raw),
         compressed_bytes=len(raw),files=inventory,read_only_estimate=estimate,local_disk=space))
    print(json.dumps(dict(project=project,job_id=job,files=len(files),archive_bytes=len(raw))))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('inspect','stage','preflight','submit','status','fetch'))
    parser.add_argument('project',choices=('stdlib',))
    args=parser.parse_args()
    if args.action=='inspect':inspect_remote(args.project)
    else:globals()[args.action](args.project)

