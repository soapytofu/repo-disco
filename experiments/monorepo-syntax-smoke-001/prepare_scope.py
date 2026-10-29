"""Prepare an eight-call proposal using unchanged clarified prompts. Offline only."""
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent/'monorepo-calibration-syntax-001'/'frozen-001'
PARENT_SHA = 'cfa8ae517c07751f45591ce52d91c3f63240dee167f9ffbdf83b5a282799cd32'
# Same depth within every pair; opposite first conditions for two families each.
# One sample per task. Selection is structural, not based on past response outcome.
ORDER = ['conditional-deep-shared', 'transfer-deep-separate',
         'offset-deep-separate', 'witness-deep-shared',
         'conditional-deep-separate', 'transfer-deep-shared',
         'offset-deep-shared', 'witness-deep-separate']


def load(p):
    return json.loads(p.read_text())


def save(p, obj):
    p.write_text(json.dumps(obj, indent=2)+'\n')


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def validate_bundle(p):
    frozen=load(p/'freeze.json')
    names={str(f.relative_to(p)) for f in p.rglob('*') if f.is_file()}-{'freeze.json'}
    if names != set(frozen['files']):
        raise ValueError('Frozen file-set drift')
    for name, expected in frozen['files'].items():
        if sha(p/name) != expected:
            raise ValueError('Frozen hash drift: '+name)


def prepare(out):
    if sha(PARENT/'freeze.json') != PARENT_SHA:
        raise ValueError('Unexpected clarified-prompt freeze')
    validate_bundle(PARENT)
    out.mkdir(exist_ok=False)
    for name in ['guard']:
        shutil.copytree(PARENT/name,out/name)
    shutil.copy2(PARENT/'system.txt',out/'system.txt')
    settings=load(PARENT/'settings.json')
    settings.update(max_calls=8,independent_samples_per_variant=1,
                    status='PROPOSED_NOT_AUTHORIZED',model_calls_made=0)
    save(out/'settings.json',settings)
    parent_tasks={t['task_id']:t for t in load(PARENT/'tasks.json')}
    parent_trials={t['task_id']:t for t in load(PARENT/'trials.json') if t['sample']==1}
    tasks=[];trials=[]
    for i,task_id in enumerate(ORDER,1):
        task=parent_tasks[task_id]
        shutil.copytree(PARENT/'tasks'/task_id,out/'tasks'/task_id)
        tasks.append(task)
        trials.append(dict(trial_id='smoke-%02d'%i,task_id=task_id,
            family=task['family'],cell=task['depth']+'_'+task['sharing'],sample=1,
            prompt_path='tasks/'+task_id+'/prompt.txt',prompt_sha256=task['prompt_sha256'],
            system_path='system.txt',system_sha256=sha(out/'system.txt'),
            source_trial_id=parent_trials[task_id]['trial_id'],fresh_context=True,feedback=False))
    save(out/'tasks.json',tasks);save(out/'trials.json',trials)
    selected=set(ORDER)
    save(out/'preflight-gate.json',[g for g in load(PARENT/'preflight-gate.json') if g['task_id'] in selected])
    scope=dict(status='PROPOSED_NOT_AUTHORIZED',purpose='Check clarified output syntax before a larger evaluation',
        parent_freeze_sha256=PARENT_SHA,proposed_max_new_calls=8,model_calls_made=0,
        per_task_calls=1,automatic_retries=False,sdk_total_max_attempts=1,reassign_unused=False,
        independent_fresh_contexts=True,feedback=False,selection='All four development families, deep only, shared and separate; one sample each',
        order_rationale='Two families shared first, two separate first; paired tasks four positions apart; all deep tasks selected regardless of prior outputs',
        primary_metric='Exact JSON/body syntax and guard admission out of 8 planned trials',
        secondary_metrics=['Strict whole-workspace verifier exit-zero out of 8 planned trials',
                           'Syntax, guard, proof, timeout and infrastructure outcomes reported separately',
                           'Request IDs, SDK attempts, token usage and immutable source/contract hashes'],
        review_gate=dict(required_for_syntax_readiness=['Eight unambiguous saved responses',
            '8/8 admitted by the unchanged body-json-v2.1 guard',
            'Protected source and contract integrity checks pass',
            'Each admitted candidate has a terminal verifier success or proof-failure result; no infrastructure ambiguity'],
            any_syntax_failure='Do not scale; inspect saved evidence offline without silent repair or rescoring',
            proof_outcomes='Review each family separately; 0/2 and 2/2 are diagnostic floors/ceilings, not reliable difficulty estimates',
            full_32='Never automatic. Requires human review, separately frozen execution scope and a new call authorization',
            pooling='Do not pool these selectively deep smoke trials into a later fresh 32-trial evaluation'),
        stopping_rule='Stop on ambiguous request, source drift, persistence failure or verifier infrastructure error; no retry or reassignment. Syntax/guard/proof failures are saved outcomes and do not trigger repair calls.',
        maximum_output_tokens=8*settings['inference_config']['maxTokens'],
        token_note='32768 is an output-token cap, not expected consumption or a cap on input tokens. No dollar estimate.',
        limitations=['No shallow tasks; cannot estimate a depth effect','One sample per configuration; not a sharing-effect study',
                    'All families are inspected development data','Offline prompt validation does not establish model adherence'],
        runner_gate=['Separate tested bounded runner and runtime hash freeze',
                     'Explicit new eight-call authorization bound to scope and runtime',
                     'Inspect existing ledger/submission state; submit once on a live-confirmed nonpreemptible compute partition',
                     'Private credential handoff only after authorization; no connectivity model calls'],
        publication='Save exact messages/responses, extraction decisions, admitted source, raw verifier logs, ledger, hashes, request IDs, failures and concise report; exclude credentials')
    save(out/'scope.json',scope)
    (out/'README.md').write_text('''# Eight-call syntax smoke proposal: not authorized

All four deep development tasks, shared and separate, one fresh response each.
Prompts, sources, parser and model settings are copied exactly from the clarified
syntax bundle; only selection/order and the proposed eight-call limit change.
No live runner, authorization or credential access is included. No requests or
new verifier runs have occurred. scope.json defines reporting and review gates.
''')
    save(out/'freeze.json',dict(status='PROPOSED_NOT_AUTHORIZED',model_calls=0,trial_count=8,
        files={str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file()}))
    return out


if __name__=='__main__':
    print(prepare(ROOT/'frozen-001'))
