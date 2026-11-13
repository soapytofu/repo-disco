"""Twenty-four independent one-round repairs; frozen feedback masking, no retries."""
from collections import Counter
import hashlib, importlib.util, json, math, os, re, shutil, socket, subprocess, sys, time
from pathlib import Path
from types import MappingProxyType
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'agent'))
import target_metrics
import repair_protocol
from repository_agent import RevisionStore
from language.dafny.candidate import prepare_candidate, PreparedCandidate
from language.dafny.repository import RepositoryVerification
from language import VerificationOutput, VerificationOutcome
from logging_verifier import verify as verify_logged
from bounded_requests import RequestGate, bedrock_transport, consume_key, durable_json
PROPOSAL_SHA='fb2c86885e80fa7dea146b90ae701971cf021d81c908d66d2b6816880f98e672'
LIMIT=24
NORMAL_OUTCOMES={'VERIFIED','PROOF_FAILURE','FRONTEND_ERROR','WARNING_ONLY','OUTPUT_REJECTED','OUTPUT_TRUNCATED'}
RUNTIME_FILES={'runner-tests.log', 'logging_verifier.py', 'agent/language/__init__.py', 'agent/language/dafny/prompt.py', 'agent/repository_agent.py', 'ops.py', 'agent/execute.py', 'agent/language/dafny/repository.py', 'review_results.py', 'model.sbatch', 'environment_preflight.py', 'bounded_requests.py', 'agent/language/dafny/__init__.py', 'agent/language/dafny/candidate.py', 'repair_protocol.py', 'run_pilot.py', 'target_metrics.py', 'test_runner.py'}

def load(path):
    return json.loads(path.read_text())

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def hashes(files):
    return {n: hashlib.sha256(b).hexdigest() for n, b in sorted(files.items())}

def inventory(root):
    return {str(p.relative_to(root)): sha(p) for p in sorted(root.rglob('*')) if p.is_file()}

def require(condition, message):
    if not condition:
        raise ValueError(message)

def measurement(evidence,task,root=ROOT):
    outcome=outcome_for_evidence(evidence)
    if outcome not in ('VERIFIED','PROOF_FAILURE','WARNING_ONLY'):
        return dict(available=False,reason='No completed proof-level verification'),False
    try:
        require(evidence['command']==['timeout','-k','5s','60s','dafny','verify','--verify-included-files','--log-format','csv','All.dfy'],'Logger command mismatch')
        require(evidence['attempts']==1 and evidence['model_calls']==0,'Logger provenance mismatch')
        require({n:hashlib.sha256(t.encode()).hexdigest() for n,t in evidence['csv'].items()}==evidence['csv_sha256'],'Logger digest mismatch')
        scope=load(root/'frozen-001/measurement-scope.json')['tasks'][task['task_id']]
        score=target_metrics.scores(evidence['csv'],scope,{n:set(k) for n,k in scope['expected_units'].items()})
        if outcome=='VERIFIED':
            require(score['supplied_providers_verified'] and all(score['local_targets'].values()),'Strict success has failed logger targets')
        return dict(available=True,**score),False
    except (KeyError,ValueError,TypeError) as error:
        return dict(available=False,reason='Logger interpretation failed',error_type=type(error).__name__,detail=str(error)),True

def outcome_for_evidence(evidence):
    code = evidence.get('exit_code')
    text = evidence['stdout'] + '\n' + evidence['stderr']
    summaries = re.findall(r'^Dafny program verifier finished with (\d+) verified, (\d+) errors?\s*$',
                           text, re.MULTILINE)
    no_errors = len(summaries) == 1 and int(summaries[0][0]) > 0 and int(summaries[0][1]) == 0 and ': Error:' not in text
    if code == 0:
        return 'VERIFIED' if no_errors and 'warning' not in text.lower() else 'EVIDENCE_MISMATCH'
    if code == 4:
        return 'PROOF_FAILURE'
    if code == 2:
        if no_errors and ': Warning:' in text and '--allow-warnings is false' in text:
            return 'WARNING_ONLY'
        return 'FRONTEND_ERROR'
    return 'VERIFIER_STOP'


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result

def policy(root=ROOT):
    return (module('repair_body',root/'frozen-001/policy/body_guard.py'),
            module('repair_envelope',root/'frozen-001/policy/extract_response.py'))

def files(path):return {p.name:p.read_bytes() for p in sorted(path.glob('*.dfy'))}

def parent_parts(root,trial):
    row=load(root/'frozen-001/parents.json')[trial['parent_id']]
    task=load(root/'frozen-001'/row['task_path'])
    return row,task,files(root/'frozen-001'/row['base_path']),files(root/'frozen-001'/row['template_path'])

def validate_bundle(root=ROOT):
    frozen=root/'frozen-001'
    require(sha(frozen/'freeze.json')==PROPOSAL_SHA,'Proposal changed')
    freeze=load(frozen/'freeze.json');actual=inventory(frozen);actual.pop('freeze.json')
    require(actual==freeze['files'],'Frozen payload changed')
    require(inventory(root/'inputs')==freeze['repository_inputs_sha256'],'Dependency changed')
    plan=load(frozen/'settings.json');trials=load(frozen/'trials.json');parents=load(frozen/'parents.json')
    require(plan['proposed_calls']==LIMIT and plan['max_calls_per_trial']==1 and plan['sdk_total_max_attempts']==1
            and not plan['automatic_retries'] and not plan['reassign_unused'] and not plan['feedback_after_repair'],'Budget scope')
    require([t['trial_id'] for t in trials]==[f'diverse-repair-{i:02d}' for i in range(1,LIMIT+1)],'Order drift')
    require([[t['semantic_instance'],t['sharing'],t['feedback_condition']] for t in trials]==plan['order'],'Condition order')
    for trial in trials:
        row,task,base,template=parent_parts(root,trial)
        require(hashes(base)==row['source_sha256'] and hashes(template)==task['source_sha256'],'Parent drift')
        require(sha(frozen/trial['request_path'])==trial['request_sha256'],'Request drift')
        evidence=load(frozen/row['original_verifier_path'])
        require(evidence['source_sha256']==hashes(base) and outcome_for_evidence(evidence)=='PROOF_FAILURE','Original evidence')
    return plan,parents,trials

def validate_runtime(root=ROOT):
    pins=load(root/'runtime-freeze.json')
    require(pins['proposal_freeze_sha256']==PROPOSAL_SHA and pins['max_calls']==LIMIT
            and not pins['automatic_retries'] and not pins['reassign_unused'],'Runtime scope')
    require(set(pins['runtime_sha256'])==RUNTIME_FILES,'Runtime inventory')
    for name,h in pins['runtime_sha256'].items():require(sha(root/name)==h,'Runtime changed: '+name)
    scope=load(root/'frozen-001/measurement-scope.json')
    require(scope['interpreter_sha256']==sha(root/'target_metrics.py'),'Metric interpreter changed')
    require(sha(root/'repair_protocol.py')==sha(root/'frozen-001/policy/repair_protocol.py'),'Repair adapter changed')
    return pins

def decode(raw,root,trial):
    row,task,base,template=parent_parts(root,trial);guard,envelope=policy(root)
    # Distinguish envelope rejection while retaining the frozen adapter unchanged.
    try:envelope.extract_json(raw)
    except (ValueError,TypeError,UnicodeError,RecursionError) as e:raise OutputRejected('envelope',e) from e
    try:
        edited,decision=repair_protocol.apply_response(raw,{n:b.decode() for n,b in base.items()},
            {n:b.decode() for n,b in template.items()},task,row['source_sha256'],guard,envelope)
    except (ValueError,TypeError,UnicodeError,RecursionError) as e:raise OutputRejected('body_guard',e) from e
    return {n:s.encode() for n,s in edited.items()},decision

def prepared(base,edited,task):
    def check(name):
        def guard(old,new):
            require(old==base.files[name] and new==edited[name],'Adapter byte mismatch')
        return guard
    replacements={n:edited[n] for n in task['editable_files']}
    if edited==base.files:
        # A no-op is a valid failed repair, not a grammar failure. Verify it once.
        return PreparedCandidate(MappingProxyType(dict(edited)),MappingProxyType(hashes(base.files)),
                                 MappingProxyType(hashes(edited)),(),task['entry'])
    return prepare_candidate(base.files,replacements,entry=task['entry'],expected_hashes=hashes(base.files),
                             guards={n:check(n) for n in replacements})

def create_store(folder,root,trial):
    row,task,base,template=parent_parts(root,trial)
    manifest=dict(task_id=task['task_id'],entry=task['entry'],editable=task['editable_files'],
        dependencies={n:re.findall(r'^include "([^"]+)"',b.decode(),re.M) for n,b in base.items()})
    store=RevisionStore.create(folder/'store',base,manifest);snapshot=store.snapshot()
    durable_json(folder/'initial.json',dict(revision=snapshot.revision,source_sha256=hashes(base),
        evidence_path=row['original_verifier_path'],evidence_sha256=sha(root/'frozen-001'/row['original_verifier_path']),
        reused_original_verification=True,new_verifier_runs=0))
    return store,snapshot

def evaluate(trial,response,folder,verifier,root,store,base):
    _,task,seed,_=parent_parts(root,trial)
    require(base.files==seed,'Store starting bytes')
    raw=response.get('text')
    if not isinstance(raw,str):return dict(outcome='RESPONSE_ERROR',stop=True)
    if response.get('stop_reason')=='max_tokens':
        durable_json(folder/'extraction.json',dict(accepted=False,stage='truncation'))
        return dict(outcome='OUTPUT_TRUNCATED',stop=False)
    try:edited,decision=decode(raw,root,trial)
    except OutputRejected as error:
        durable_json(folder/'extraction.json',dict(accepted=False,stage=error.stage,error_type=type(error.__cause__).__name__,reason=str(error)))
        return dict(outcome='OUTPUT_REJECTED',stop=False)
    candidate=prepared(base,edited,task)
    durable_json(folder/'extraction.json',dict(accepted=True,**decision))
    dest=folder/'candidate';dest.mkdir()
    for n,b in edited.items():(dest/n).write_bytes(b)
    durable_json(folder/'candidate-hashes.json',dict(parent_sha256=hashes(seed),candidate_sha256=hashes(edited)))
    try:evidence=verifier(edited)
    except Exception as error:return dict(outcome='VERIFIER_ERROR',stop=True,error_type=type(error).__name__)
    durable_json(folder/'verification.json',evidence)
    require(evidence['source_sha256']==hashes(edited),'Verifier source mismatch')
    outcome=outcome_for_evidence(evidence);metrics,stop=measurement(evidence,task,root)
    durable_json(folder/'target-metrics.json',metrics)
    for n,s in evidence.get('csv',{}).items():
        p=Path(n);require(not p.is_absolute() and '..' not in p.parts,'Unsafe logger path')
        dest=folder/'raw-csv'/p;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(s.encode())
    if outcome=='VERIFIED' and not stop:
        result=RepositoryVerification(VerificationOutput(VerificationOutcome.SUCCESS,0,evidence['stdout'],evidence['stderr']),evidence)
        try:revision=store.promote(base,candidate,result)
        except ValueError as error:return dict(outcome='PROMOTION_REJECTED',stop=True,reason=str(error))
        durable_json(folder/'accepted.json',dict(base_revision=base.revision,revision=revision,parent_sha256=hashes(seed),
            candidate_sha256=hashes(edited),verification_sha256=sha(folder/'verification.json')))
    return dict(outcome=outcome,stop=stop or outcome not in NORMAL_OUTCOMES,measurement_available=metrics['available'])


class OutputRejected(ValueError):
    def __init__(self, stage, error):
        self.stage=stage
        super().__init__(str(error))

def validate_authorization(root, now):
    auth = load(root / 'authorization.json')
    require(auth.get('authorized') is True and auth.get('max_calls') == LIMIT
            and auth.get('automatic_retries') is False and auth.get('reassign_unused') is False,
            'New 24-call authorization required')
    require(auth.get('proposal_freeze_sha256') == PROPOSAL_SHA
            and auth.get('runtime_freeze_sha256') == sha(root / 'runtime-freeze.json'), 'Authorization pins')
    expiry = auth.get('expires_at_epoch')
    require(type(expiry) in (int, float) and math.isfinite(expiry) and now < expiry <= now + 86400,
            'Expired or invalid authorization')
    require(bool(auth.get('authorization_basis')), 'Missing human authorization basis')
    return auth, expiry

def collect(out, transport, verifier, deadline, *, root=ROOT, clock=time.time, check_runtime=True):
    plan, tasks, trials = validate_bundle(root)
    if check_runtime:
        validate_runtime(root)
    out = Path(out)
    
    gate = RequestGate(out / 'requests', LIMIT, deadline, transport, clock=clock)
    rows, request_ids = [], set()
    fatal = None
    try:
        for trial in trials:
            validate_bundle(root)
            if check_runtime:
                validate_runtime(root)
            _,task,seed,_ = parent_parts(root,trial)
            folder = out / trial['trial_id']
            folder.mkdir()
            durable_json(folder / 'trial.json', trial)
            durable_json(folder / 'task.json', task)
            store,base=create_store(folder,root,trial)
            request_path = root / 'frozen-001' / trial['request_path']
            shutil.copy2(request_path, folder / 'request.json')
            started = clock()
            try:
                response = gate.invoke(load(request_path), task_id=task['task_id'], attempt_id=trial['trial_id'])
            except Exception as error:
                row = dict(**trial, outcome='REQUEST_STOP', error_type=type(error).__name__, stop=True)
                durable_json(folder / 'result.json', row)
                rows.append(row)
                durable_json(out / 'results.json', rows)
                break
            durable_json(folder / 'response.json', response)
            rid = response.get('request_id')
            if not isinstance(rid, str) or not rid or rid in request_ids or response.get('retry_attempts') != 0:
                result = dict(outcome='REQUEST_METADATA_STOP', stop=True)
            else:
                request_ids.add(rid)
                result = evaluate(trial,response,folder,verifier,root,store,base)
            row = dict(**trial, request_id=rid, retry_attempts=response.get('retry_attempts'),
                       usage=response.get('usage'), stop_reason=response.get('stop_reason'),
                       elapsed_seconds=clock()-started, **result)
            require(seed == parent_parts(root,trial)[2], 'Seed mutation')
            head=store.snapshot()
            require((head.revision!=base.revision)==(row['outcome']=='VERIFIED' and not row['stop']), 'Promotion outcome mismatch')
            durable_json(folder/'final-head.json',dict(revision=head.revision,source_sha256=hashes(head.files)))
            durable_json(folder / 'result.json', row)
            rows.append(row)
            durable_json(out / 'results.json', rows)
            print(trial['trial_id'], row['outcome'], flush=True)
            if row['stop']:
                break
    except BaseException as error:
        fatal = type(error).__name__
        raise
    finally:
        completed = len(rows) == LIMIT and all(r['outcome'] in NORMAL_OUTCOMES and not r['stop'] for r in rows)
        if not gate.closed:
            gate.close('finished' if completed else 'stopped')
        reservations = gate.state['reservations']
        durable_json(out / 'summary.json', dict(maximum_calls=LIMIT, reserved_calls=len(reservations),
                     dispatch_started=sum('dispatch_started_at_epoch' in r for r in reservations),
                     completed_responses=sum(r['status'] == 'COMPLETED' for r in reservations),
                     verified=sum(r['outcome'] == 'VERIFIED' for r in rows),
                     fatal_error_type=fatal, all_trials_processed=completed,
                     unused_calls_not_reassigned=LIMIT-len(reservations), results=rows))
    return rows

def archive_runtime(root, out, auth):
    durable_json(out / 'authorization.json', auth)
    shutil.copytree(root / 'frozen-001', out / 'frozen-001')
    shutil.copytree(root / 'inputs', out / 'inputs')
    shutil.copy2(root / 'runtime-freeze.json', out / 'runtime-freeze.json')
    (out / 'runtime').mkdir()
    for name in RUNTIME_FILES:
        dest = out / 'runtime' / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / name, dest)

def main():
    require(sys.argv[1:] == ['run'], 'Only explicit fresh run mode is supported')
    require(os.environ.get('SLURM_JOB_ID') and 'login' not in socket.gethostname(), 'Compute allocation required')
    plan, _, _ = validate_bundle()
    validate_runtime()
    auth, deadline = validate_authorization(ROOT, time.time())
    out = ROOT / 'model-001'
    out.mkdir(exist_ok=False)
    archive_runtime(ROOT, out, auth)
    from importlib.metadata import version
    env = dict(job_id=os.environ['SLURM_JOB_ID'], partition=os.environ.get('SLURM_JOB_PARTITION'),
               host=socket.gethostname(), python=sys.version,
               packages={p: version(p) for p in ('boto3', 'botocore')},
               dafny=subprocess.run(['dafny', '--version'], capture_output=True, text=True, check=True, timeout=15).stdout.strip(),
               z3=subprocess.run(['z3', '--version'], capture_output=True, text=True, check=True, timeout=15).stdout.strip())
    durable_json(out / 'environment.json', env)
    require(env['dafny'] == plan['verifier']['toolchain'] and env['z3'] == plan['verifier']['z3'], 'Toolchain mismatch')
    try:
        consume_key(Path.home() / '.repodisco-bedrock-handoff')
        rows = collect(out, bedrock_transport(plan), verify_logged, deadline)
        require(len(rows) == LIMIT and all(row['outcome'] in NORMAL_OUTCOMES and not row['stop'] for row in rows),
                'Incomplete batch; manual ledger review required')
    finally:
        os.environ.pop('AWS_BEARER_TOKEN_BEDROCK', None)

if __name__=='__main__':main()
