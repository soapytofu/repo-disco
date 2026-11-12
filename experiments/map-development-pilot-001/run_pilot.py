"""Prospective sixteen-request batch; authorization is required for live execution."""
from collections import Counter
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import time
import target_metrics
from logging_verifier import verify as verify_logged

sys.dont_write_bytecode = True
from bounded_requests import RequestGate, bedrock_transport, consume_key, durable_json

ROOT = Path(__file__).resolve().parent
PROPOSAL_SHA = '84211b3fd2286cc0b6c8cb5b139c6856dc214270c09762c9dcc0f03f0fbe2097'
LIMIT = 16
PLAN_PATH = Path('experiments/map-development-plan-001/plan.json')
RUNTIME_FILES = {'run_pilot.py', 'bounded_requests.py', 'test_runner.py',
                 'environment_preflight.py', 'review_results.py', 'model.sbatch', 'runner-tests.log', 'ops.py', 'readiness-gate.json',
                 'logging_verifier.py', 'target_metrics.py'}
NORMAL_OUTCOMES = {'VERIFIED', 'PROOF_FAILURE', 'FRONTEND_ERROR', 'WARNING_ONLY',
                   'OUTPUT_REJECTED', 'OUTPUT_TRUNCATED'}


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


def sources(root, task):
    directory = root / 'frozen-001/seeds' / task['task_id']
    return {p.name: p.read_bytes() for p in directory.glob('*.dfy')}


def source_root(root, task):
    plan=load(root/'frozen-001/settings.json')
    return root/'inputs/experiments'/plan['source_experiments'][task['semantic_instance']]


def validate_bundle(root=ROOT):
    frozen = root / 'frozen-001'
    require(sha(frozen / 'freeze.json') == PROPOSAL_SHA, 'Proposal digest changed')
    freeze = load(frozen / 'freeze.json')
    actual = inventory(frozen)
    actual.pop('freeze.json')
    require(actual == freeze['files'], 'Frozen payload files changed')
    require(inventory(root / 'inputs') == freeze['repository_inputs_sha256'], 'Pinned dependency files changed')
    plan = load(root / 'inputs' / PLAN_PATH)
    tasks = load(frozen / 'tasks.json')
    trials = load(frozen / 'trials.json')
    require(plan['proposed_calls'] == LIMIT and plan['sdk_total_max_attempts'] == 1
            and not plan['feedback'] and not plan['reassign_unused'], 'Budget policy drift')
    require([t['trial_id'] for t in trials] == [f'map-dev-{i:02d}' for i in range(1, LIMIT+1)], 'Trial identity/order')
    require([t['task_id'] for t in trials] ==
            [task_id for replicate in plan['replicates'] for task_id in replicate], 'Cell order')
    require(len(tasks) == 8 and Counter(t['task_id'] for t in trials) ==
            {t['task_id']: 2 for t in tasks}, 'Task coverage')
    for task in tasks:
        require(hashes(sources(root, task)) == task['source_sha256'], 'Seed changed')
    for trial in trials:
        require(sha(frozen / trial['request_path']) == trial['request_sha256'], 'Request changed')
    return plan, tasks, trials


def validate_runtime(root=ROOT):
    pins = load(root / 'runtime-freeze.json')
    require(pins['proposal_freeze_sha256'] == PROPOSAL_SHA and pins['max_calls'] == LIMIT
            and not pins['automatic_retries'] and not pins['reassign_unused'], 'Runtime scope drift')
    require(set(pins['runtime_sha256']) == RUNTIME_FILES, 'Incomplete runtime inventory')
    for name, expected in pins['runtime_sha256'].items():
        require(sha(root / name) == expected, 'Runtime changed: ' + name)
    gate = load(root / 'readiness-gate.json')
    require(gate['proposal_freeze_sha256'] == PROPOSAL_SHA and gate['primary_controls'] == 76,
            'Readiness scope drift')
    primary_path=root/'frozen-001/reviewed-controls.json'
    require(sha(primary_path)==gate['primary_report_sha256'],'Primary evidence drift')
    require(Counter(x['diagnostic'] for x in load(primary_path))==
            dict(success=8,proof_failure=60,resolution_failure=8),'Primary coverage')
    require(sha(root/'frozen-001/target-scope.json')==gate['target_scope_sha256'],'Measurement scope drift')
    scope=load(root/'frozen-001/target-scope.json')
    require(scope['interpretation_sha256']==sha(root/'target_metrics.py'),'Interpreter changed')
    require(sha(root/'inputs/experiments/target-completion-diagnostic-001/target-review.json')==
            scope['diagnostic_report_sha256'],'Measurement evidence drift')
    require(gate['new_model_calls']==0 and gate['measurement_controls']==5,'Gate provenance')
    return pins


def validate_authorization(root, now):
    auth = load(root / 'authorization.json')
    require(auth.get('authorized') is True and auth.get('max_calls') == LIMIT
            and auth.get('automatic_retries') is False and auth.get('reassign_unused') is False,
            'New sixteen-call authorization required')
    require(auth.get('proposal_freeze_sha256') == PROPOSAL_SHA
            and auth.get('runtime_freeze_sha256') == sha(root / 'runtime-freeze.json'), 'Authorization pins')
    expiry = auth.get('expires_at_epoch')
    require(type(expiry) in (int, float) and math.isfinite(expiry) and now < expiry <= now + 86400,
            'Expired or invalid authorization')
    require(bool(auth.get('authorization_basis')), 'Missing human authorization basis')
    return auth, expiry


class OutputRejected(ValueError):
    def __init__(self, stage, error):
        self.stage=stage
        super().__init__(str(error))


def guard_module(root):
    def module(name,path):
        spec=importlib.util.spec_from_file_location(name,path)
        result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result
    bindings=load(root/'frozen-001/policy-bindings.json')
    bodies={tid:module(tid.replace('-','_')+'_body',root/'frozen-001'/row['body_guard']) for tid,row in bindings.items()}
    envelopes={tid:module(tid.replace('-','_')+'_envelope',root/'frozen-001'/row['envelope']) for tid,row in bindings.items()}
    class ComposedGuard:
        split_seed=staticmethod(next(iter(bodies.values())).split_seed)
        @staticmethod
        def parse_response(raw,seeds,task):
            body=bodies[task['task_id']];envelope=envelopes[task['task_id']]
            try:payload,span=envelope.extract_json(raw)
            except (ValueError,TypeError,UnicodeError,RecursionError) as e:raise OutputRejected('envelope',e) from e
            try:candidate,decision=body.parse_response(payload,seeds,task)
            except (ValueError,TypeError,UnicodeError,RecursionError) as e:raise OutputRejected('body_guard',e) from e
            return candidate,dict(envelope=span,body_guard=decision)
    return ComposedGuard()


def measurement(evidence,task,root=ROOT):
    outcome=outcome_for_evidence(evidence)
    if outcome not in ('VERIFIED','PROOF_FAILURE','WARNING_ONLY'):
        return dict(available=False,reason='No completed proof-level verification'),False
    try:
        require(evidence['command']==['timeout','-k','5s','60s','dafny','verify','--verify-included-files','--log-format','csv','All.dfy'],'Logger command mismatch')
        require(evidence['attempts']==1 and evidence['model_calls']==0,'Logger provenance mismatch')
        require({n:hashlib.sha256(t.encode()).hexdigest() for n,t in evidence['csv'].items()}==evidence['csv_sha256'],'Logger digest mismatch')
        scope=load(root/'frozen-001/target-scope.json')['tasks'][task['task_id']]
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


def evaluate(task, seed, response, folder, verifier, guard, root=ROOT):
    raw = response.get('text')
    if not isinstance(raw, str):
        return dict(outcome='RESPONSE_ERROR', stop=True)
    if response.get('stop_reason') == 'max_tokens':
        durable_json(folder / 'extraction.json', dict(accepted=False, stage='truncation'))
        return dict(outcome='OUTPUT_TRUNCATED', stop=False)
    try:
        edited, decision = guard.parse_response(raw, {n: b.decode() for n, b in seed.items()}, task)
    except (ValueError, TypeError, UnicodeError, RecursionError) as error:
        durable_json(folder / 'extraction.json', dict(accepted=False, stage=getattr(error,'stage','body_guard'),
                                                     error_type=type(error).__name__, reason=str(error)))
        return dict(outcome='OUTPUT_REJECTED', stop=False)
    candidate = {n: text.encode() for n, text in edited.items()}
    require(set(candidate) == set(seed), 'Candidate file-set changed')
    for name, original in seed.items():
        if name in task['editable_files']:
            prefix, suffix = guard.split_seed(original.decode())
            require(candidate[name].startswith(prefix.encode()) and candidate[name].endswith(suffix.encode()),
                    'Protected body boundary changed')
        else:
            require(candidate[name] == original, 'Protected file changed')
    durable_json(folder / 'extraction.json', dict(accepted=True, **decision))
    dest = folder / 'candidate'
    dest.mkdir()
    for name, content in candidate.items():
        (dest / name).write_bytes(content)
    durable_json(folder / 'candidate-hashes.json',
                 dict(parent_sha256=hashes(seed), candidate_sha256=hashes(candidate)))
    try:
        evidence = verifier(candidate)
    except Exception as error:
        return dict(outcome='VERIFIER_ERROR', stop=True, error_type=type(error).__name__)
    durable_json(folder / 'verification.json', evidence)
    require(evidence.get('source_sha256') == hashes(candidate), 'Verifier candidate hash mismatch')
    outcome = outcome_for_evidence(evidence)
    metrics,measurement_stop=measurement(evidence,task,root)
    durable_json(folder/'target-metrics.json',metrics)
    for name,text in evidence.get('csv',{}).items():
        path=Path(name)
        require(not path.is_absolute() and '..' not in path.parts,'Unsafe logger filename')
        dest=folder/'raw-csv'/path;dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_bytes(text.encode())
    if outcome == 'VERIFIED':
        durable_json(folder / 'accepted.json', dict(parent_sha256=hashes(seed), candidate_sha256=hashes(candidate),
                     editable_files=task['editable_files'], verification_sha256=sha(folder / 'verification.json')))
    return dict(outcome=outcome, stop=outcome not in NORMAL_OUTCOMES or measurement_stop,
                measurement_available=metrics['available'])


def collect(out, transport, verifier, deadline, *, root=ROOT, clock=time.time, check_runtime=True):
    plan, tasks, trials = validate_bundle(root)
    if check_runtime:
        validate_runtime(root)
    out = Path(out)
    guard = guard_module(root)
    gate = RequestGate(out / 'requests', LIMIT, deadline, transport, clock=clock)
    rows, request_ids = [], set()
    fatal = None
    try:
        for trial in trials:
            validate_bundle(root)
            if check_runtime:
                validate_runtime(root)
            task = next(t for t in tasks if t['task_id'] == trial['task_id'])
            seed = sources(root, task)
            folder = out / trial['trial_id']
            folder.mkdir()
            durable_json(folder / 'trial.json', trial)
            durable_json(folder / 'task.json', task)
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
                result = evaluate(task, seed, response, folder, verifier, guard, root)
            row = dict(**trial, request_id=rid, retry_attempts=response.get('retry_attempts'),
                       usage=response.get('usage'), stop_reason=response.get('stop_reason'),
                       elapsed_seconds=clock()-started, **result)
            require(hashes(seed) == hashes(sources(root, task)) == task['source_sha256'], 'Seed mutation')
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


if __name__ == '__main__':
    main()
