"""Operator-only second admission; never creates a job, provider or budget owner.

prepare is local. stage writes only a new immutable data bundle. check/inspect
are read-only remotely. admit publishes one data descriptor for the existing
owner. A failed/ambiguous stage or admit remains locked: there is no retry API.
"""
import argparse
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path, PurePosixPath
import shlex
import subprocess
import sys
import tarfile
import time

sys.dont_write_bytecode = True
WINDOW_ID = 'repodisco-research-20261114'
BATCH = 'repository-repair-selection-001'
FIRST = 'repair-diversity-pilot-002'
FIRST_RUN = '0001-' + FIRST
JOB = '60698074'
DEADLINE = 1794801912.0
FREEZE = '9a3ac2546edc6c79307826766af3517bdc8d9a8fe629a2ba0239660f4ead778a'
RUNTIME = 'ca24194ab90c932e0c514c1b390a80dd999645ccf07a9c937ea176f82b701b44'
SCOPE = 'a649bcfca3be0b1120f8c7810778a344dd6fbf395dbeb6b6e362a20c5541ed01'
PREVIOUS = 'de2516e216666522cb6ef3eaac6f35bb67f716fb31a4ee917a8ba688e8a9f73f'
PREVIOUS_LEDGER = '1a0281f6c4e3022b9d434194a1d7c987c8979ce0c41fc942c10300450ac4f6b7'
PREVIOUS_RECEIPT = '29505eabe3c17d431549baae3369db871db45def4eedf85fa72035df57b0ead7'
HANDLER = '546f2677b14fbb742e16c0263146e6947a7a533e5ccfe26f7fe47377ebd3eb16'
REMOTE = '/n/home13/sophiezeng/formal-disco/outputs/research-window-20261114'
PYTHON = '/n/home13/sophiezeng/.conda/envs/repodisco/bin/python'


def require(value, message):
    if not value: raise ValueError(message)


def canonical(value): return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
def digest(raw): return hashlib.sha256(raw).hexdigest()
def sha(path): return digest(path.read_bytes())


def pairs(items):
    result = {}
    for key,value in items:
        require(key not in result, 'Duplicate JSON key')
        result[key] = value
    return result


def loads(raw):
    def reject(value): raise ValueError('Nonstandard JSON')
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=reject)


def load(path): return loads(path.read_bytes())


def safe(root, name):
    require(isinstance(name,str) and name and '\\' not in name, 'Relative path required')
    p = PurePosixPath(name)
    require(not p.is_absolute() and all(x not in ('','.','..') for x in name.split('/')), 'Unsafe path')
    require(root.is_dir() and not root.is_symlink(), 'Regular root required')
    out = root
    for piece in p.parts:
        out /= piece
        require(not out.is_symlink(), 'Symlink forbidden')
    return out


def inventory(root):
    require(root.is_dir() and not root.is_symlink(), 'Regular directory required')
    result = {}
    for path in sorted(root.rglob('*')):
        require(not path.is_symlink() and (path.is_file() or path.is_dir()), 'Nonregular entry')
        if path.is_file(): result[path.relative_to(root).as_posix()] = sha(path)
    return result


def sync_dir(path):
    fd = os.open(path, os.O_RDONLY | getattr(os,'O_DIRECTORY',0))
    try: os.fsync(fd)
    finally: os.close(fd)


def exclusive(path, raw):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os,'O_NOFOLLOW',0), 0o600)
    with os.fdopen(fd,'wb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    sync_dir(path.parent)


def sync_tree(root, expected):
    require(inventory(root)==expected, 'Input inventory/hash drift')
    for name,h in sorted(expected.items()):
        path = safe(root,name)
        with path.open('rb') as stream:
            require(digest(stream.read())==h, 'Input changed before fsync')
            os.fsync(stream.fileno())
        require(sha(path)==h, 'Input changed during fsync')
    for path in sorted((p for p in root.rglob('*') if p.is_dir()),key=lambda p:len(p.parts),reverse=True):
        sync_dir(path)
    sync_dir(root); sync_dir(root.parent)
    require(inventory(root)==expected, 'Input drift after durable staging')


def driver(window):
    """Check exact code before importing the existing data-validation APIs."""
    runtime = safe(window,'execution-runtime')
    require(sha(safe(runtime,'runtime-freeze.json'))==RUNTIME, 'Execution freeze changed')
    freeze = load(runtime/'runtime-freeze.json')
    require(inventory(runtime)==dict(freeze['runtime_sha256'],**{'runtime-freeze.json':RUNTIME}), 'Execution inventory changed')
    require(digest(canonical(freeze['runtime_sha256']))==HANDLER, 'Handler binding changed')
    require(sha(safe(window,'scope.json'))==SCOPE, 'Scope changed')
    for name,h in freeze['dependencies_sha256'].items():
        require(name.startswith(('../runtime/','../session-runtime-002/')), 'Unexpected code dependency')
        require(sha(safe(window,name[3:]))==h, 'Dependency changed')
    path = runtime/'session_driver.py'
    spec = importlib.util.spec_from_file_location('admission_fixed_session_driver',path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def descriptor_for(window, bundle):
    d = driver(window)
    plan,parents,trials = d.batch.validate_bundle(bundle)
    d.batch.validate_runtime(bundle)
    binding = load(bundle/'batch-binding.json')
    expected = dict(window_id=WINDOW_ID,batch_id=BATCH,max_calls=32,proposal_freeze_sha256=FREEZE,
                    runtime_freeze_sha256=RUNTIME,authorized=True,automatic_retries=False,
                    max_calls_per_trial=1,model_settings=d.model_settings())
    require(binding==expected and plan['study']==BATCH and len(trials)==32, 'Batch scope changed')
    for trial in trials:
        request = load(safe(bundle/'frozen-001',trial['request_path']))
        require(set(request)=={'modelId','system','messages','inferenceConfig'} and
                request['modelId']==d.batch.ALLOWED_MODEL and request['inferenceConfig']==d.batch.ALLOWED_INFERENCE,
                'Request settings changed')
    return dict(schema=d.coordination.SCHEMA,sequence=2,previous_descriptor_sha256=PREVIOUS,
                batch_id=BATCH,handler_id='repair-v1',handler_binding_sha256=HANDLER,artifact_directory=BATCH,
                freeze_path='frozen-001/freeze.json',freeze_sha256=FREEZE,runtime_path='runtime-freeze.json',
                runtime_sha256=RUNTIME,input_sha256=inventory(bundle),max_calls=32,sdk_total_max_attempts=1,
                slots=[dict(trial_id=t['trial_id'],request_path='frozen-001/'+t['request_path'],
                            request_sha256=t['request_sha256']) for t in trials])


def prepare(window, repo, output):
    d = driver(window)
    source = safe(repo,'experiments/repository-repair-selection-001/pilot/frozen-001')
    require(sha(source/'freeze.json')==FREEZE, 'Reviewed proposal freeze changed')
    frozen = load(source/'freeze.json')
    require(inventory(source)==dict(frozen['files'],**{'freeze.json':FREEZE}), 'Frozen inventory changed')
    bundle = window/'batches'/BATCH
    require(not bundle.exists() and not bundle.is_symlink(), 'No prepare restart')
    output.mkdir(parents=True,exist_ok=False)
    bundle.mkdir(mode=0o700)
    pins = {'frozen-001/'+n:h for n,h in dict(frozen['files'],**{'freeze.json':FREEZE}).items()}
    pins.update({'inputs/'+n:h for n,h in frozen['repository_inputs_sha256'].items()})
    for name,h in sorted(pins.items()):
        source_path = safe(source,name[len('frozen-001/'):]) if name.startswith('frozen-001/') else safe(repo,name[len('inputs/'):])
        raw = source_path.read_bytes(); require(digest(raw)==h, 'Source changed')
        dest = safe(bundle,name); dest.parent.mkdir(parents=True,exist_ok=True); exclusive(dest,raw)
    exclusive(bundle/'runtime-freeze.json',(window/'execution-runtime/runtime-freeze.json').read_bytes())
    exclusive(bundle/'batch-binding.json',canonical(dict(window_id=WINDOW_ID,batch_id=BATCH,max_calls=32,
        proposal_freeze_sha256=FREEZE,runtime_freeze_sha256=RUNTIME,authorized=True,automatic_retries=False,
        max_calls_per_trial=1,model_settings=d.model_settings()))+b'\n')
    descriptor = descriptor_for(window,bundle)
    sync_tree(bundle,descriptor['input_sha256'])
    exclusive(output/'descriptor.json',canonical(descriptor)+b'\n')
    exclusive(output/'preparation.json',canonical(dict(batch_id=BATCH,files=len(descriptor['input_sha256']),
        descriptor_sha256=sha(output/'descriptor.json'),proposal_freeze_sha256=FREEZE,
        runtime_freeze_sha256=RUNTIME,maximum_calls=32,model_calls=0))+b'\n')
    return descriptor


def scheduler():
    raw = subprocess.run(['squeue','-j',JOB,'-h','-o','%i|%T|%N|%Z'],capture_output=True,text=True,
                         timeout=10,check=True).stdout
    rows = [line.split('|') for line in raw.strip().splitlines()]
    require(len(rows)==1 and len(rows[0])==4, 'One existing owner job required')
    job,state,node,workdir = rows[0]
    return dict(job_id=job,state=state,node=node,workdir=workdir)


def audit(window, descriptor, *, staged, job_probe=scheduler, clock=time.time):
    """Read-only, canonical existing-owner checks; never acquires/reopens a gate."""
    require(clock()<DEADLINE, 'Window expired')
    d = driver(window)
    scope,freeze = d.validate_execution(window,SCOPE,RUNTIME)
    job = job_probe()
    require(job['job_id']==JOB and job['state']=='RUNNING' and job['workdir']==REMOTE, 'Existing job is not running here')
    require(not any(safe(window,n).exists() for n in ['STOP','SEAL','session-001/STOP','session-001/SEAL']), 'Operator stop/seal')
    admissions = safe(window,'admissions')
    require(inventory(admissions)=={'000001.json':PREVIOUS}, 'Second/unknown admission already exists')
    first = load(admissions/'000001.json')
    require(first['batch_id']==FIRST and first['sequence']==1 and first['runtime_sha256']==RUNTIME, 'First binding differs')
    require(inventory(safe(window,'batches/'+FIRST))==first['input_sha256'], 'First inputs changed')
    queue = safe(window,'session-001/queue')
    require(inventory(queue)=={'0001-'+FIRST+'.json':PREVIOUS}, 'Unexpected queued batch')
    require(sorted(p.name for p in safe(window,'session-001/runs').iterdir())==[FIRST_RUN], 'Unexpected batch output')
    require({p.name for p in window.iterdir() if p.name.startswith('submission-')}=={'submission-001.lock','submission-001.json'}, 'Extra submission evidence')
    require(load(safe(window,'submission-001.json'))['job_id']==JOB, 'Wrong submission')
    state = load(safe(window,'session-001/status.json'))
    require(state['phase']=='completed' and state['reason']=='batch_complete' and state['active_batch_id'] is None
            and state['completed_batch_ids']==[FIRST] and state['window_reservations']==32
            and state['queued']==[dict(batch_id=FIRST,descriptor_sha256=PREVIOUS,sequence=1)]
            and state['deadline_epoch']==DEADLINE, 'Session not idle after exactly one completed batch')
    require(sha(safe(window,'budget/ledger.json'))==PREVIOUS_LEDGER, 'Published predecessor ledger changed')
    ledger = load(safe(window,'budget/ledger.json'))
    require(ledger['schema']==d.w.SCHEMA and ledger['scope']==scope and
            ledger['scope_sha256']==digest(canonical(scope)) and ledger['terminal_reason'] is None, 'Global ledger scope/terminal state')
    owner = load(safe(window,'budget/owner.lock/owner.json'))
    session_owner = load(safe(window,'session-001/owner.json'))
    require(owner==ledger['owner_session'] and session_owner==load(safe(window,'budget/research-session.lock/owner.json'))
            and owner['pid']==session_owner['pid'] and owner['host'].split('.')[0]==job['node']
            and session_owner['scope_sha256']==ledger['scope_sha256']
            and session_owner['window_gate_sha256']==sha(window/'runtime/window_budget.py')
            and session_owner['coordinator_sha256']==sha(window/'session-runtime-002/coordinator.py'), 'Owner binding changed')
    manifest = {k:first[k] for k in ['batch_id','freeze_sha256','runtime_sha256','max_calls','sdk_total_max_attempts']}
    manifest['slots'] = [{k:s[k] for k in ['trial_id','request_sha256']} for s in first['slots']]
    manifest_hash = digest(canonical(manifest))
    require(ledger['batches']==[dict(manifest=manifest,manifest_sha256=manifest_hash)], 'Declared calls must remain exactly 32')
    rows = ledger['reservations']
    require(len(rows)==32 and len({r['request_id'] for r in rows})==32, 'Exactly 32 unique completed reservations required')
    for i,(row,slot) in enumerate(zip(rows,manifest['slots']),1):
        require(row['sequence']==i and row['status']=='COMPLETED' and row['batch_id']==FIRST
                and row['manifest_sha256']==manifest_hash and row['trial_id']==slot['trial_id']
                and row['request_sha256']==slot['request_sha256'] and row['request_id'], 'Ambiguous or altered reservation')
    old = safe(window,'session-001/runs/'+FIRST_RUN)
    require(sha(old/'completion.json')==PREVIOUS_RECEIPT, 'Published predecessor receipt changed')
    receipt = load(old/'completion.json')
    require(receipt['batch_id']==FIRST and receipt['descriptor_sha256']==PREVIOUS and
            receipt['completed_trials']==[s['trial_id'] for s in first['slots']] and
            receipt['request_ids']==[r['request_id'] for r in rows], 'Prior completion receipt differs')
    require(inventory(old)==dict(receipt['evidence_sha256'],**{'completion.json':sha(old/'completion.json')}), 'Prior evidence changed')
    require(not set(s['trial_id'] for s in descriptor['slots']) & set(r['trial_id'] for r in rows), 'Reused global slot')
    require(descriptor['max_calls']==32 and 32+descriptor['max_calls']<=scope['max_calls']==128, 'Aggregate cap')
    bundle = safe(window,'batches/'+BATCH)
    if staged: require(descriptor_for(window,bundle)==descriptor, 'Second data bundle differs')
    else: require(not bundle.exists(), 'Second bundle already exists; no restaging')
    require(clock()<DEADLINE, 'Window expired during audit')
    return dict(job=job,completed=32,reserved=32,declared=32,remaining_before=96,
                next_calls=32,descriptor_sha256=digest(canonical(descriptor)+b'\n'),checked_at_epoch=clock())


def remote_stage(window, descriptor, archive, *, job_probe=scheduler, clock=time.time):
    audit(window,descriptor,staged=False,job_probe=job_probe,clock=clock)
    entries = {}
    with tarfile.open(fileobj=io.BytesIO(archive),mode='r:gz') as tar:
        for member in tar.getmembers():
            require(member.isfile() and member.name not in entries, 'Nonregular/duplicate archive member')
            safe(window,member.name)
            entries[member.name] = tar.extractfile(member).read()
    require({n:digest(b) for n,b in entries.items()}==descriptor['input_sha256'], 'Staging archive mismatch')
    lock = window/'stage-003.lock'
    exclusive(lock,canonical(dict(batch_id=BATCH,descriptor_sha256=digest(canonical(descriptor)+b'\n'),at_epoch=clock()))+b'\n')
    target = window/'batches'/BATCH; target.mkdir(mode=0o700)
    for name,raw in sorted(entries.items()):
        dest=safe(target,name);dest.parent.mkdir(parents=True,exist_ok=True);exclusive(dest,raw)
    sync_tree(target,descriptor['input_sha256'])
    result = audit(window,descriptor,staged=True,job_probe=job_probe,clock=clock)
    result.update(staged_files=len(entries),admission_published=False,model_calls=0)
    exclusive(window/'stage-003.json',canonical(result)+b'\n')
    return result


def remote_admit(window, descriptor, *, job_probe=scheduler, clock=time.time):
    require(load(safe(window,'stage-003.json'))['descriptor_sha256']==digest(canonical(descriptor)+b'\n'), 'Missing stage receipt')
    audit(window,descriptor,staged=True,job_probe=job_probe,clock=clock)
    attempt = window/'admission-002.lock'
    exclusive(attempt,canonical(dict(batch_id=BATCH,descriptor_sha256=digest(canonical(descriptor)+b'\n'),at_epoch=clock()))+b'\n')
    # Lock is permanent, including fsync, timeout, drift and pre-publication failures.
    sync_tree(window/'batches'/BATCH,descriptor['input_sha256'])
    raw = canonical(descriptor)+b'\n'
    temporary = window/'admission-002.descriptor.tmp'
    exclusive(temporary,raw)
    result = audit(window,descriptor,staged=True,job_probe=job_probe,clock=clock)
    require(temporary.read_bytes()==raw and clock()<DEADLINE, 'Descriptor changed/deadline elapsed')
    destination = window/'admissions/000002.json'
    # Hard-link creation is atomic and refuses an existing destination. No
    # replace/rename overwrite and no unlink/retry. Both names retain exact bytes.
    os.link(temporary,destination,follow_symlinks=False)
    sync_dir(destination.parent)
    result.update(admission_published=True,admission_sha256=sha(destination),owner_job=JOB)
    exclusive(window/'admission-002.json',canonical(result)+b'\n')
    return result


def remote_inspect(window):
    result = {'job':scheduler()}
    for name in ['stage-003.lock','stage-003.json','admission-002.lock','admission-002.descriptor.tmp','admission-002.json','admissions/000002.json']:
        path=safe(window,name);result[name]=sha(path) if path.is_file() else None
    result['session']=load(safe(window,'session-001/status.json'))
    ledger=load(safe(window,'budget/ledger.json'))
    result['budget']=dict(reserved=len(ledger['reservations']),completed=sum(r['status']=='COMPLETED' for r in ledger['reservations']),
        declared=sum(b['manifest']['max_calls'] for b in ledger['batches']),terminal_reason=ledger['terminal_reason'])
    return result


def remote_call(action, descriptor=None, archive=None):
    """One hard-bounded SSH invocation, no automatic retry or fallback socket."""
    source=Path(__file__).read_text()
    code='import sys,json\nfrom pathlib import Path\nns={"__name__":"reviewed_admission_helper"}\nexec(compile('+repr(source)+',"<admission-helper>","exec"),ns)\n'
    code+='root=Path('+repr(REMOTE)+')\nline=sys.stdin.buffer.readline(8*1024*1024)\nassert line.endswith(b"\\n")\ndescriptor=json.loads(line)\n'
    if action=='stage': expression='ns["remote_stage"](root,descriptor,sys.stdin.buffer.read())'
    elif action=='admit': expression='ns["remote_admit"](root,descriptor)'
    elif action=='check': expression='ns["audit"](root,descriptor,staged=True)'
    else: expression='ns["remote_inspect"](root)'
    code+='print(json.dumps('+expression+',sort_keys=True))\n'
    command=['ssh','-S',str(Path.home()/'.ssh/repodisco-codex-17.sock'),'-o','BatchMode=yes','-o','ConnectTimeout=8',
             '-o','ProxyCommand=false','sophiezeng@login.rc.fas.harvard.edu',shlex.quote(PYTHON)+' -B -c '+shlex.quote(code)]
    # Descriptor inventories are larger than some platforms' single-argument
    # limit. Data travels on stdin, never in a shell argument or environment.
    payload=canonical(descriptor)+b'\n'+(archive or b'')
    result=subprocess.run(command,input=payload,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=120)
    if result.returncode: raise RuntimeError('Remote action did not confirm success; inspect only, never retry')
    return loads(result.stdout)


def operator_action(action, window, preparation, *, transport=remote_call):
    if action=='inspect': return transport(action)
    descriptor=load(preparation/'descriptor.json')
    require(descriptor_for(window,window/'batches'/BATCH)==descriptor, 'Prepared descriptor drift')
    if action=='check': return transport(action,descriptor)
    require(action in ('stage','admit'), 'Unknown mutation')
    exclusive(preparation/(action+'-attempt.lock'),canonical(dict(action=action,descriptor_sha256=sha(preparation/'descriptor.json'),at_epoch=time.time()))+b'\n')
    archive=None
    if action=='stage':
        output=io.BytesIO()
        with tarfile.open(fileobj=output,mode='w:gz') as tar:
            for name in sorted(descriptor['input_sha256']):tar.add(window/'batches'/BATCH/name,arcname=name,recursive=False)
        archive=output.getvalue()
    try: result=transport(action,descriptor,archive)
    except BaseException as error:
        exclusive(preparation/(action+'-unconfirmed.json'),canonical(dict(error_type=type(error).__name__,action=action,inspect_only=True))+b'\n')
        raise
    exclusive(preparation/(action+'-receipt.json'),canonical(result)+b'\n')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['prepare','stage','check','admit','inspect'])
    args=parser.parse_args()
    here=Path(__file__).resolve().parent;window=here.parent;repo=window.parent.parent
    output=here/'prepared-001'
    if args.action=='prepare':
        value=prepare(window,repo,output);print(json.dumps(dict(files=len(value['input_sha256']),slots=len(value['slots']),model_calls=0)))
    else:print(json.dumps(operator_action(args.action,window,output),indent=2))
