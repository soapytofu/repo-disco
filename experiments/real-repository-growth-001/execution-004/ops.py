"""Explicit, single-submission controls for the unapproved eight-slot proposal.

This module does not create authorization. Handoff content is never read here.
All transport calls have hard timeouts and use only an authenticated shared socket.
"""
import argparse
import datetime
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
REL = "experiments/real-repository-growth-001/execution-004"
REMOTE_SUFFIX = "formal-disco/outputs/real-repository-growth-001/execution-004"
SOCKET = Path.home() / ".ssh/repodisco-codex-21.sock"
HOST = "sophiezeng@login.rc.fas.harvard.edu"
REMOTE_PYTHON = "/n/home13/sophiezeng/.conda/envs/repodisco/bin/python"
JOB_NAME = "growth-model-8-004"
JOB_SECONDS = 14400


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def save(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)


def write(path, value):
    save(path, (json.dumps(value, indent=2, sort_keys=True) + "\n").encode())


def validate_package():
    import runtime
    return runtime.validate_package(REPO)


def validate_authorization(path):
    import runtime
    return runtime.validate_authorization(Path(path), REPO)


def fresh_execution(root, *, forbid_authorization=True):
    root = Path(root)
    for name in ("model-001", "startup-failure.json", "execution.claim.json"):
        require(not (root / name).exists() and not (root / name).is_symlink(), "Existing output: inspect; never restart")
    require(not list((root / "submissions").glob("model.*")), "Existing submission/intention: never resubmit")
    require(not list(root.glob("*ledger*")), "Existing ledger: never reuse or reassign")
    if forbid_authorization:
        require(not (root / "authorization.json").exists(), "Existing remote authorization: inspect; never overwrite")


def private_handoff_metadata(path):
    """lstat only; deliberately never open/read/hash the credential."""
    path = Path(path)
    info = path.lstat()
    require(stat.S_ISREG(info.st_mode) and not stat.S_ISLNK(info.st_mode), "Handoff must be a regular private file")
    import os
    require(info.st_uid == os.getuid() and stat.S_IMODE(info.st_mode) == 0o600,
            "Handoff owner/permissions differ")
    require(0 < info.st_size <= 65536, "Handoff metadata size invalid")
    return dict(regular_file=True, owner_uid=info.st_uid, permissions="0600", bytes=info.st_size,
                content_read=False)


def partition_seconds(text):
    values = dict(re.findall(r"(?:^|\s)([A-Za-z][A-Za-z0-9]*)=(\S+)", text))
    require(values.get("PartitionName") == "shared" and values.get("PreemptMode") == "OFF" and
            values.get("State") == "UP", "Shared partition is not live-confirmed nonpreemptible/UP")
    maximum = values.get("MaxTime", "")
    if maximum == "UNLIMITED":
        return None
    match = re.fullmatch(r"(?:(\d+)-)?(\d+):(\d{2}):(\d{2})", maximum)
    require(match is not None, "Unknown partition time limit")
    days, hours, minutes, seconds = (int(x or 0) for x in match.groups())
    require(minutes < 60 and seconds < 60, "Malformed partition time limit")
    total = ((days * 24 + hours) * 60 + minutes) * 60 + seconds
    require(total >= JOB_SECONDS, "Shared partition cannot fit the fixed four-hour request")
    return total


def no_matching_queue(queue, root):
    for line in queue.splitlines():
        fields = line.split("|")
        require(len(fields) == 4, "Malformed queue listing")
        require(fields[1] != str(root) and fields[2] != JOB_NAME, "Matching execution job already queued")

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
    require(isinstance(job,str) and re.fullmatch(r'[1-9][0-9]*',job),'Invalid parent JobID')
    require(isinstance(accounting,str),'Accounting must be decoded text')
    lines=[line for line in accounting.splitlines() if line.strip()]
    require(lines and tuple(x.strip() for x in lines[0].split('|'))==ACCOUNTING_FIELDS,
              'Unexpected accounting header')
    rows=[];seen=set();ignored=[]
    for line in lines[1:]:
        values=[x.strip() for x in line.split('|')]
        require(len(values)==len(ACCOUNTING_FIELDS),'Malformed accounting row')
        row=dict(zip(ACCOUNTING_FIELDS,values));ident=row['JobID']
        require(bool(ident),'Missing accounting JobID')
        if ident!=job and not ident.startswith(job+'.'):
            ignored.append(ident);continue
        if ident!=job:
            require(re.fullmatch(re.escape(job)+r'\.[A-Za-z0-9_-]+',ident),
                      'Malformed relevant step JobID')
        require(ident not in seen,'Duplicate parent or step accounting row')
        seen.add(ident);state=row['State']
        if state.endswith('+'):state=state[:-1].rstrip()
        match=re.fullmatch(r'([A-Z_]+)(?: by ([0-9]+))?',state)
        require(match is not None and (match.group(2) is None or match.group(1)=='CANCELLED'),
                  'Unknown accounting state syntax for '+ident)
        base=match.group(1)
        require(base in TERMINAL_STATES,'Nonterminal or unknown accounting state for '+ident+': '+row['State'])
        rows.append(dict(job_id=ident,state=row['State'],normalized_state=base,
                         kind='parent' if ident==job else 'step'))
    require(sum(row['job_id']==job for row in rows)==1,'Missing exact parent accounting row')
    return dict(parent_job_id=job,rows=rows,ignored_job_ids=ignored,all_relevant_rows_terminal=True,
                accounting_sha256=hashlib.sha256(accounting.encode()).hexdigest())


CHECK = r'''import hashlib,json,sys
expected=EXPECTED_RUNTIME
repo=root/'repo'
code=repo/'experiments/real-repository-growth-001/execution-004'
assert hashlib.sha256((root/'runtime-freeze.json').read_bytes()).hexdigest()==expected
assert (root/'runtime-freeze.json').read_bytes()==(code/'runtime-freeze.json').read_bytes()
freeze=json.loads((root/'runtime-freeze.json').read_bytes())
assert freeze['schema']=='repodisco-growth-execution-runtime-v1'
from pathlib import PurePosixPath
for name,digest in freeze['repo_files'].items():
 p=PurePosixPath(name)
 assert not p.is_absolute() and '..' not in p.parts and '\\' not in name
 target=repo/name;current=target
 while current!=repo:
  assert not current.is_symlink(),name
  current=current.parent
 assert target.is_file() and hashlib.sha256(target.read_bytes()).hexdigest()==digest,name
assert (root/'run.sbatch').read_bytes()==(code/'run.sbatch').read_bytes()
sys.path.insert(0,str(code))
'''


def remote(code, data=None, seconds=45, socket=SOCKET):
    socket = Path(socket)
    require(socket.is_absolute() and "\x00" not in str(socket), "Absolute authenticated socket path required")
    argv = ['ssh', '-S', str(socket), '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=8',
            '-o', 'ProxyCommand=false', HOST]
    prefix = "from pathlib import Path\nroot=Path.home()/" + repr(REMOTE_SUFFIX) + "\n"
    code = code.replace('EXPECTED_RUNTIME', repr(sha(ROOT / 'runtime-freeze.json')))
    command = ' '.join(shlex.quote(part) for part in (REMOTE_PYTHON, '-B', '-c', prefix + code))
    result = subprocess.run(argv + [command], input=data,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=seconds)
    if result.stderr:
        print(result.stderr.decode(errors='replace'), file=sys.stderr)
    result.check_returncode()
    return result.stdout


def stage(socket=SOCKET):
    """After explicit root release, stage exact nonsecret package once."""
    validate_package()
    require(not any((ROOT / name).exists() for name in ('stage-001.json', 'stage.intent.json')),
            'Existing staging state: inspect; never restage')
    freeze = read(ROOT / 'runtime-freeze.json')
    archive = io.BytesIO()
    with tarfile.open(fileobj=archive, mode='w:gz') as tar:
        for name in sorted(freeze['repo_files']):
            tar.add(REPO / name, arcname='repo/' + name, recursive=False)
        for name, destination in [('runtime-freeze.json', 'runtime-freeze.json'),
                                  ('runtime-freeze.json', 'repo/' + REL + '/runtime-freeze.json'),
                                  ('run.sbatch', 'run.sbatch')]:
            tar.add(ROOT / name, arcname=destination, recursive=False)
    write(ROOT / 'stage.intent.json', dict(runtime_sha256=sha(ROOT / 'runtime-freeze.json'),
                                         model_calls=0, native_calls=0, no_retry=True))
    program = r'''import io,tarfile,sys,json
from pathlib import PurePosixPath
assert not root.exists(),'Destination exists: inspect; never restage'
data=sys.stdin.buffer.read()
with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as tar:
 names=set()
 for member in tar.getmembers():
  path=PurePosixPath(member.name)
  assert member.isfile() and not path.is_absolute() and '..' not in path.parts and '\\' not in member.name
  assert member.name not in names
  names.add(member.name)
 root.mkdir(parents=True)
 for member in tar.getmembers():
  target=root/member.name;target.parent.mkdir(parents=True,exist_ok=True)
  with target.open('xb') as stream:stream.write(tar.extractfile(member).read())
'''+CHECK+r'''
print(json.dumps(dict(root=str(root),runtime_sha256=expected,model_calls=0,native_calls=0)))
'''
    raw = remote(program, archive.getvalue(), seconds=180, socket=socket)
    save(ROOT / 'stage-001.json', raw)
    print(raw.decode())


def preflight(socket=SOCKET):
    require(not (ROOT / 'remote-preflight-001.json').exists(), 'Remote preflight already recorded')
    program = CHECK+r'''import os,signal,subprocess,time
assert not (root/'remote-preflight-001.json').exists(),'Remote preflight already recorded'
evidence=root/'preflight-evidence-001'
assert not evidence.exists() and not evidence.is_symlink(),'Preflight evidence already exists'
command=[str(Path.home()/'.conda/envs/repodisco/bin/python'),'-B',str(code/'preflight.py'),
         '--repo',str(repo),'--require-sdk','--evidence-dir',str(evidence)]
driver_timed_out=False
child=subprocess.Popen(command,cwd=str(code),stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
def kill_owned_group():
 try:os.killpg(child.pid,signal.SIGKILL)
 except ProcessLookupError:pass
try:
 try:
  stdout,stderr=child.communicate(timeout=900)
 except subprocess.TimeoutExpired:
  driver_timed_out=True
  kill_owned_group()
  stdout,stderr=child.communicate(timeout=10)
finally:
 # A directly exited preflight may still have nested tests writing its log.
 # Units and SDK probes inherit this owned group; neither starts a new session.
 kill_owned_group()
 child.wait(timeout=10)
 deadline=time.monotonic()+5
 while True:
  try:os.killpg(child.pid,0)
  except ProcessLookupError:break
  if time.monotonic()>=deadline:raise RuntimeError('Preflight group still exists; evidence snapshot refused')
  time.sleep(0.05)
process=subprocess.CompletedProcess(command,124 if driver_timed_out else child.returncode,stdout=stdout,stderr=stderr)
try:
 result=json.loads(process.stdout.decode())
 assert result['returncode']==process.returncode
except (ValueError,KeyError,AssertionError):
 result=dict(schema='repodisco-growth-execution-offline-preflight-v1',returncode=process.returncode or 1,process_returncode=process.returncode,
  log=process.stdout.decode(errors='replace'),preflight_record_parse_failed=True,runtime_sha256=expected,
  model_calls=0,native_calls=0)
result['driver_stderr']=process.stderr.decode(errors='replace')
result['driver_timed_out']=driver_timed_out
result['driver_timeout_seconds']=900
result['driver_process_group_reaped']=True
result['preflight_evidence']={}
for name in ('started.json','sdk-imports.json','sdk-auth-regression.json','unit-tests.log','unit-result.json','result.json'):
 path=evidence/name
 if path.exists():
  assert path.is_file() and not path.is_symlink(),'Nonregular preflight evidence'
  raw=path.read_bytes()
  result['preflight_evidence'][name]=dict(sha256=hashlib.sha256(raw).hexdigest(),text=raw.decode(errors='replace'))
with (root/'remote-preflight-001.json').open('x') as stream:json.dump(result,stream,indent=2)
print(json.dumps(result))
'''
    raw = remote(program, seconds=1050, socket=socket)
    save(ROOT / 'remote-preflight-001.json', raw)
    result = json.loads(raw)
    print(result['log'])
    require(result['returncode'] == 0, 'Remote fake-only preflight failed')


SUBMIT = CHECK+r'''import datetime,os,re,subprocess
import runtime
from ops import fresh_execution,private_handoff_metadata,partition_seconds,no_matching_queue
runtime.validate_package(repo)
fresh_execution(root)
pre=json.loads((root/'remote-preflight-001.json').read_bytes())
assert pre['returncode']==0 and pre['runtime_sha256']==expected
assert pre['sdk']['required'] is True and pre['sdk']['installed'] is True and pre['sdk']['client_created'] is False
assert pre['sdk']['config']==dict(connect_timeout=15,read_timeout=180,retries=dict(mode='standard',total_max_attempts=1))
sdk_auth=pre['sdk_auth_regression']
assert sdk_auth['status']=='PASS' and sdk_auth['required'] is True and sdk_auth['returncode']==0 and sdk_auth['scenarios']==5
assert sdk_auth['record']['status']=='PASS' and sdk_auth['record']['real_credentials_read'] is False
assert all(sdk_auth['record'][field]==0 for field in ('model_calls','native_calls','provider_requests','socket_connection_attempts'))
raw_authorization=sys.stdin.buffer.read()
# This is a verbatim copy of an explicit human authorization supplied to ops,
# not construction of an authorization from a prior or inferred budget.
with (root/'authorization.json').open('xb') as stream:stream.write(raw_authorization)
authorization=runtime.validate_authorization(root/'authorization.json',repo)
assert authorization['authorized_runtime_root']==str(root)
assert repo.parent==root and authorization['output_relative_path']=='model-001'
handoff=private_handoff_metadata(Path.home()/'.repodisco-bedrock-handoff')
queue=subprocess.check_output(['squeue','-u','sophiezeng','-h','-o','%i|%Z|%j|%T'],text=True,timeout=15)
no_matching_queue(queue,root)
partition=subprocess.check_output(['scontrol','show','partition','shared'],text=True,timeout=15)
maximum=partition_seconds(partition)
record=dict(schema='repodisco-growth-exclusive-submission-v1',
 utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),runtime_sha256=expected,
 authorization_sha256=hashlib.sha256(raw_authorization).hexdigest(),
 partition='shared',partition_record=partition,prior_queue=queue,
 resources=dict(cpus=1,memory_gb=8,job_seconds=14400,no_requeue=True),
 handoff_metadata=handoff,submission_attempts=1,automatic_retry=False)
sub=root/'submissions';sub.mkdir(exist_ok=True)
with (sub/'model.lock').open('x') as stream:json.dump(record,stream,indent=2)
try:
 process=subprocess.run(['sbatch','--parsable','--partition=shared','run.sbatch'],cwd=str(root),
     stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=25)
 record.update(returncode=process.returncode,stdout=process.stdout,stderr=process.stderr)
 if process.returncode==0:
  match=re.fullmatch(r'([1-9][0-9]*)(?:;[A-Za-z0-9_.-]+)?\s*',process.stdout)
  if match:record['job_id']=match.group(1)
  else:record['ambiguous_submission']=True
except subprocess.TimeoutExpired:
 record['ambiguous_submission']=True
 record['error_type']='TimeoutExpired'
with (sub/'model.json').open('x') as stream:json.dump(record,stream,indent=2)
print(json.dumps(record))
'''


def submit(authorization, socket=SOCKET):
    """Exactly one attempt, only after separately supplied fresh authorization."""
    validate_package()
    authorization = Path(authorization)
    validate_authorization(authorization)  # before transport or local intent
    raw_authorization = authorization.read_bytes()
    fresh_execution(ROOT, forbid_authorization=False)
    sub = ROOT / 'submissions'
    write(sub / 'model.intent.json', dict(runtime_sha256=sha(ROOT / 'runtime-freeze.json'),
          authorization_sha256=hashlib.sha256(raw_authorization).hexdigest(),
          utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), maximum_submission_attempts=1,
          retries=False, state='INTENT_REQUIRES_READ_ONLY_REVIEW_IF_NO_RECEIPT'))
    try:
        raw = remote(SUBMIT, raw_authorization, seconds=100, socket=socket)
    except BaseException as error:
        write(sub / 'model.transport-failure.json', dict(type=type(error).__name__,
              submission_outcome_requires_read_only_review=True, automatic_retry=False))
        raise
    save(sub / 'model.json', raw)
    record = json.loads(raw)
    print(json.dumps({key: value for key, value in record.items() if key not in ('partition_record', 'prior_queue')}, indent=2))
    require('job_id' in record and not record.get('ambiguous_submission'),
            'Submission failed or ambiguous; preserve intent and do not retry')


def status(socket=SOCKET):
    job = read(ROOT / 'submissions/model.json')['job_id']
    require(re.fullmatch(r'[1-9][0-9]*', job), 'Invalid submission JobID')
    program = 'job=' + repr(job) + '\n' + r'''import subprocess,json
result=dict(accounting=subprocess.check_output(['sacct','-j',job,'--format=JobID,State,Elapsed,ExitCode,NodeList','-P'],text=True,timeout=15))
folder=root/'model-001'
result['model_output_exists']=folder.exists()
result['startup_failure_exists']=(root/'startup-failure.json').exists()
result['completed_records']=len(list(folder.glob('*/result.json')))
result['terminal_records']=[p.name for p in folder.glob('*.json') if p.name in ('complete.json','stopped.json','summary.json')]
print(json.dumps(result))
'''
    print(remote(program, seconds=30, socket=socket).decode())


def transfer_inventory(root, job, accounting, terminal_review):
    """Read-only regular-file inventory of results, never the credential."""
    root = Path(root)
    names = ['submissions/model.lock', 'submissions/model.json', 'authorization.json',
             'runtime-freeze.json', 'remote-preflight-001.json']
    require(all((root / name).is_file() for name in names), 'Missing submission/authorization/provenance evidence')
    # A native/startup failure can precede model-001. Preserve exactly what exists.
    for name in ('startup-failure.json', 'execution.claim.json'):
        if (root / name).exists():
            names.append(name)
    if (root / 'model-001').exists():
        import runtime
        require((root / 'model-001').is_dir() and not (root / 'model-001').is_symlink(), 'Nonregular model evidence root')
        names += [path.relative_to(root).as_posix() for path in runtime.archive_files(root / 'model-001')]
        if (root / 'model-001/archive-manifest.json').exists():
            names.append('model-001/archive-manifest.json')
    names += sorted(path.name for path in root.glob('growth-' + job + '.*'))
    require(any(name.startswith('model-001/') or name == 'startup-failure.json' or name.startswith('growth-') for name in names),
            'No run or scheduler evidence exists')
    inventory = {}

    def visit(path):
        mode = path.lstat().st_mode
        require(not stat.S_ISLNK(mode), 'Symlink in transfer evidence')
        if stat.S_ISDIR(mode):
            for child in sorted(path.iterdir()):
                visit(child)
        else:
            require(stat.S_ISREG(mode), 'Nonregular transfer evidence')
            data = path.read_bytes()
            inventory[path.relative_to(root).as_posix()] = dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
    for name in names:
        visit(root / name)
    virtual = {'accounting.txt': accounting.encode(),
               'accounting-review.json': json.dumps(terminal_review, indent=2, sort_keys=True).encode()}
    for name, data in virtual.items():
        require(not (root / name).exists(), 'Accounting/archive already created: inspect; never refetch')
        inventory[name] = dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
    return dict(source_bytes=sum(value['bytes'] for value in inventory.values()), regular_files=len(inventory),
                inventory_sha256=hashlib.sha256(json.dumps(inventory, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
                names=sorted(inventory), job_id=job,
                excluded_scratch_directories=['model-001/slot-%02d/native/fresh-target' % index
                    for index in range(1, 9) if (root / ('model-001/slot-%02d/native/fresh-target' % index)).exists()],
                exclusions_reason='Exact generated Cargo targets only; all source workspaces and native evidence retained')


def require_fetch_space(estimate, destination):
    size, count = estimate['source_bytes'], estimate['regular_files']
    require(type(size) is int and size >= 0 and type(count) is int and count > 0, 'Invalid transfer size estimate')
    headroom = max(64 * 1024 * 1024, (size + 3) // 4)
    available = shutil.disk_usage(destination).free
    require(available >= size + headroom,
            'Insufficient local disk space before fetch; neither endpoint was changed')
    return dict(source_bytes=size, headroom_bytes=headroom, required_free_bytes=size + headroom, observed_free_bytes=available)


def fetch(socket=SOCKET):
    require(not (ROOT / 'transfer-001.json').exists(), 'Already fetched')
    destination = ROOT / 'retrieved-001'
    require(not destination.exists(), 'Existing local evidence: never partially refetch')
    job = read(ROOT / 'submissions/model.json')['job_id']
    require(re.fullmatch(r'[1-9][0-9]*', job), 'Invalid submission JobID')
    inspect = CHECK + 'job=' + repr(job) + '\n' + r'''import subprocess,json,io,tarfile
from ops import terminal_accounting,transfer_inventory
accounting=subprocess.check_output(['sacct','-j',job,'--format=JobID%40,State%80,Elapsed,ElapsedRaw,ExitCode,AllocCPUS,TotalCPU,CPUTimeRAW,MaxRSS,NodeList','-P'],text=True,timeout=15)
terminal_review=terminal_accounting(accounting,job)
inventory=transfer_inventory(root,job,accounting,terminal_review)
'''
    estimate = json.loads(remote(inspect + 'print(json.dumps(inventory))\n', seconds=90, socket=socket))
    require(estimate['job_id'] == job, 'Transfer estimate identity differs')
    disk = require_fetch_space(estimate, ROOT)
    raw = remote(inspect + 'assert inventory==' + repr(estimate) + ',"Transfer evidence changed after size estimate"\n' + r'''
with (root/'accounting.txt').open('x') as stream:stream.write(accounting)
with (root/'accounting-review.json').open('x') as stream:json.dump(terminal_review,stream,indent=2,sort_keys=True)
buffer=io.BytesIO()
with tarfile.open(fileobj=buffer,mode='w:gz') as tar:
 for name in inventory['names']:tar.add(root/name,arcname=name,recursive=False)
sys.stdout.buffer.write(buffer.getvalue())
''', seconds=180, socket=socket)
    sizes = {}
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:gz') as tar:
        for member in tar.getmembers():
            name = PurePosixPath(member.name)
            require(not name.is_absolute() and '..' not in name.parts and '\\' not in member.name, 'Unsafe archive path')
            if member.isdir():
                continue
            require(member.isfile() and str(name) not in sizes, 'Nonregular or duplicate artifact')
            data = tar.extractfile(member).read()
            sizes[str(name)] = dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
        digest = hashlib.sha256(json.dumps(sizes, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        require(digest == estimate['inventory_sha256'] and len(sizes) == estimate['regular_files'] and
                sum(value['bytes'] for value in sizes.values()) == estimate['source_bytes'], 'Archive differs from read-only estimate')
        require_fetch_space(estimate, ROOT)
        destination.mkdir()
        for member in tar.getmembers():
            if member.isfile():
                save(destination / member.name, tar.extractfile(member).read())
    write(ROOT / 'transfer-001.json', dict(files=sizes, compressed_bytes=len(raw), job_id=job,
          archive_sha256=hashlib.sha256(raw).hexdigest(), read_only_estimate=estimate, pre_fetch_disk_check=disk))
    print(json.dumps(dict(files=len(sizes), compressed_bytes=len(raw), job_id=job)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('stage', 'preflight', 'submit', 'status', 'fetch'))
    parser.add_argument('--socket', type=Path, default=SOCKET)
    parser.add_argument('--authorization', type=Path)
    args = parser.parse_args()
    require((args.action == 'submit') == (args.authorization is not None), 'Only submit requires explicit --authorization')
    if args.action == 'submit':
        submit(args.authorization, args.socket)
    else:
        globals()[args.action](args.socket)

