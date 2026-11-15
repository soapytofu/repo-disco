"""Generic reviewed one-round repair batch, always called through the window session."""
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
NORMAL_OUTCOMES={'VERIFIED','PROOF_FAILURE','FRONTEND_ERROR','WARNING_ONLY','OUTPUT_REJECTED','OUTPUT_TRUNCATED'}
ALLOWED_MODEL='global.anthropic.claude-opus-4-5-20251101-v1:0'
ALLOWED_REGION='us-east-1'
ALLOWED_INFERENCE={'temperature':1.0,'maxTokens':4096}

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
        require(score['supplied_providers_verified'],'Protected provider verification failed')
        if outcome=='VERIFIED':
            require(all(score['local_targets'].values()),'Strict success has failed logger targets')
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
    frontend=bool(re.search(r'(?:parse|resolution/type) errors? detected',text,re.I))
    if code == 4:
        coherent=len(summaries)==1 and int(summaries[0][1])>0 and ': Error:' in text and not frontend
        return 'PROOF_FAILURE' if coherent else 'EVIDENCE_MISMATCH'
    if code == 2:
        if no_errors and ': Warning:' in text and '--allow-warnings is false' in text:
            return 'WARNING_ONLY'
        return 'FRONTEND_ERROR' if frontend and ': Error:' in text else 'EVIDENCE_MISMATCH'
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
    auth=load(root/'batch-binding.json')
    require(sha(frozen/'freeze.json')==auth['proposal_freeze_sha256'],'Proposal changed')
    freeze=load(frozen/'freeze.json');actual=inventory(frozen);actual.pop('freeze.json')
    require(actual==freeze['files'],'Frozen payload changed')
    require(inventory(root/'inputs')==freeze['repository_inputs_sha256'],'Dependency changed')
    plan=load(frozen/'settings.json');trials=load(frozen/'trials.json');parents=load(frozen/'parents.json')
    limit=plan['proposed_calls']
    require(type(limit) is int and 1<=limit<=128 and limit==len(trials),'Batch limit')
    require(plan['model_id']==ALLOWED_MODEL and plan['region']==ALLOWED_REGION and plan['inference_config']==ALLOWED_INFERENCE,'Approved model/settings changed')
    require(plan['max_calls_per_trial']==1 and plan['sdk_total_max_attempts']==1
            and not plan['automatic_retries'] and not plan['reassign_unused'] and not plan['feedback_after_repair'],'Budget scope')
    require(len({t['trial_id'] for t in trials})==limit and [t['sequence'] for t in trials]==list(range(1,limit+1)),'Order drift')
    require(all(t['max_calls']==1 for t in trials),'Per-slot cap')
    require([[t['semantic_instance'],t['sharing'],t['feedback_condition']] for t in trials]==plan['order'],'Condition order')
    for trial in trials:
        row,task,base,template=parent_parts(root,trial)
        require(hashes(base)==row['source_sha256'] and hashes(template)==task['source_sha256'],'Parent drift')
        require(sha(frozen/trial['request_path'])==trial['request_sha256'],'Request drift')
        evidence=load(frozen/row['original_verifier_path'])
        require(evidence['source_sha256']==hashes(base) and outcome_for_evidence(evidence)=='PROOF_FAILURE','Original evidence')
    return plan,parents,trials

def validate_runtime(root=ROOT):
    pins=load(ROOT/'runtime-freeze.json')
    require(pins['automatic_retries'] is False,'Runtime retry policy')
    actual=inventory(ROOT);allowed=pins['runtime_sha256']
    for name,h in allowed.items():require(sha(ROOT/name)==h,'Runtime changed: '+name)
    require(sha(ROOT/'runtime-freeze.json')==load(root/'batch-binding.json')['runtime_freeze_sha256'],'Batch runtime changed')
    scope=load(root/'frozen-001/measurement-scope.json')
    require(scope['interpreter_sha256']==sha(ROOT/'target_metrics.py'),'Metric interpreter changed')
    require(sha(ROOT/'repair_protocol.py')==sha(root/'frozen-001/policy/repair_protocol.py'),'Repair adapter changed')
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
    return dict(outcome='MEASUREMENT_STOP' if stop else outcome,verifier_outcome=outcome,
                stop=stop or outcome not in NORMAL_OUTCOMES,measurement_available=metrics['available'])


class OutputRejected(ValueError):
    def __init__(self, stage, error):
        self.stage=stage
        super().__init__(str(error))


def collect(out, transport, verifier, deadline, *, root=ROOT, clock=time.time, check_runtime=True):
    plan, tasks, trials = validate_bundle(root)
    limit=len(trials)
    if check_runtime:
        validate_runtime(root)
    out = Path(out)
    
    gate = RequestGate(out / 'requests', limit, deadline, transport, clock=clock)
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
        completed = len(rows) == limit and all(r['outcome'] in NORMAL_OUTCOMES and not r['stop'] for r in rows)
        if not gate.closed:
            gate.close('finished' if completed else 'stopped')
        reservations = gate.state['reservations']
        durable_json(out / 'summary.json', dict(maximum_calls=limit, reserved_calls=len(reservations),
                     dispatch_started=sum('dispatch_started_at_epoch' in r for r in reservations),
                     completed_responses=sum(r['status'] == 'COMPLETED' for r in reservations),
                     verified=sum(r['outcome'] == 'VERIFIED' and not r.get('stop',False) for r in rows),
                     fatal_error_type=fatal, all_trials_processed=completed,
                     unused_calls_not_reassigned=limit-len(reservations), results=rows))
    return rows

def archive_runtime(root, out):
    shutil.copytree(root/'frozen-001',out/'frozen-001')
    shutil.copytree(root/'inputs',out/'inputs')
    shutil.copy2(root/'batch-binding.json',out/'batch-binding.json')
    shutil.copy2(ROOT/'runtime-freeze.json',out/'runtime-freeze.json')
    (out/'runtime').mkdir()
    for name in load(ROOT/'runtime-freeze.json')['runtime_sha256']:
        dest=out/'runtime'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,dest)

if __name__=='__main__':raise SystemExit('No standalone paid mode; use the reviewed window session')
