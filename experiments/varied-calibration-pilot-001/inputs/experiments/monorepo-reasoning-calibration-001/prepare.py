"""Offline preparation only: no SDK, credentials, SSH, jobs or verifier calls."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import shutil
import types

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent.parent
EXPERIMENT=ROOT.parent/'monorepo-reasoning-expansion-001'
SOURCE=EXPERIMENT/'revision-003'
SOURCE_COMMIT='a58400dc7278dfa77aa3b61cab4307bbc271a742'
REVIEW_SHA='888ac0a847614097a1db62f854fbbe07d497490f51c00ee28d2506e00101fdf0'
MANIFEST_SHA='38edc4d363259ed882806bd5ed521bd5567f49fadf41486548ad2bf86946a533'
GUARD_SHA='5cb8995fe7108538e9d7debb561dc75c38c895d5dd739a7bcf4673aaeeec1102'
PREVIOUS_SETTINGS=ROOT.parent/'monorepo-balanced-calibration-001/frozen-001/settings.json'
PREVIOUS_SETTINGS_SHA='fce4f6f665d7c82cb661274f666fdafe4cf2615c0ae9edc8376db883dd871c19'
CELLS=['shallow_shared','shallow_separate','deep_shared','deep_separate']
INSTANCES=['nested_clamp','reverse_concat','commuting_updates','clamp_stability','nested_filter','delete_after_update']
# First four rows are a four-treatment Williams square. Two additional rows
# balance within-depth sharing order and first depth/sharing across six instances.
ROWS=[[0,1,3,2],[1,2,0,3],[2,3,1,0],[3,0,2,1],[0,2,1,3],[3,1,2,0]]
SYSTEM='''Complete missing proof bodies in the supplied Dafny 4.11.0 monorepo workspace.
Return only one JSON object mapping exactly the requested editable filenames to
proof-body strings. No explanation, full files, declarations, or outer lemma-body
braces. The host inserts those strings into the supplied empty bodies and verifies
the entire workspace, including all providers and both clients. Preserve every
supplied signature, contract, import, induction setting and decreases clause.
Follow the explicitly bounded output language. Use braced if/else statements;
if/then/else is only a pure value expression, never a branch of lemma calls.
'''
SYNTAX_EXAMPLES=[
    'if true { assert true; } else { assert true; }',
    'var tmp := if true then 0 else 1; assert tmp == 0;',
    'var xs := [0,1]; assert |xs| == 2;',
    'forall key | key == 0 ensures key == 0 { assert key == 0; }',
]
SYNTAX='''Allowed output language (syntax examples below are illustrative, not proofs of the task):
- Semicolon-terminated assertions and calls to the listed lemmas.
- Braced if/else statements. Do not write `if condition then Call(); else Call();`.
- Fresh inferred-type locals: `var name := expression;`. No explicit local types,
  shadowing parameters/module aliases/active locals, or assignments after declaration.
- One-bound-variable proof blocks: `forall name | domain ensures property { statements }`.
  The bound name is fresh and available only inside this proof block. Use one ensures
  expression; combine multiple required facts with &&. This is a proof statement,
  not a quantified expression inside an assertion.
- Integer and boolean literals; +, -, !, comparisons, ==>, &&, ||, in and !in;
  parentheses; pure `if condition then value else value`; sequence literals, indexing
  and slices; cardinality |expression|; .Keys; and the listed pure functions.
- Calls to Prove refer only to the same helper. Its fixed decreases clause must hold.
Not allowed: comments, assumptions, expects, reveals, attributes, declarations,
imports, cross-helper calls, loops, calc/match blocks, strings, lambdas, explicit
types, map/set literals or comprehensions, map updates, multiplication/division,
unlisted operations, or arbitrary Dafny syntax. Do not bypass verification.
All calls/assertions/local declarations end with a semicolon. Do not add a semicolon
after a braced if or forall block. JSON must escape body newlines normally; do not
double-escape them into literal backslash-n tokens in the Dafny body.
Limits: 262144 UTF-8 bytes for the response; each body at most 65536 bytes, 8192
tokens and 256 statements, with at most 24 statement nesting levels and 32 expression
nesting levels. Integer literals have at most 12 digits. Syntax admission alone
does not establish proof correctness: all obligations and termination must verify.
'''


def load(p): return json.loads(p.read_text())
def save(p,obj): p.write_text(json.dumps(obj,indent=2)+'\n')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def digest(text): return hashlib.sha256(text.encode()).hexdigest()
def require(ok,message):
    if not ok: raise ValueError(message)
def inventory(path): return {str(p.relative_to(path)):sha(p) for p in sorted(path.rglob('*')) if p.is_file()}
def files(path): return {p.name:p.read_text() for p in sorted(path.glob('*.dfy'))}
def guard(path):
    # Read trusted, hash-checked code without creating bytecode inside the freeze.
    module=types.ModuleType('reasoning_frozen_guard');module.__file__=str(path)
    exec(compile(path.read_bytes(),str(path),'exec'),module.__dict__)
    return module


def validate_bundle(path):
    actual=inventory(path);actual.pop('freeze.json',None)
    require(actual==load(path/'freeze.json')['files'],'Frozen file-set/hash drift')


def body_payload(parser,task,seed,target):
    bodies={}
    for name in task['editable_files']:
        prefix,suffix=parser.split_seed(seed[name]);text=target[name]
        require(text.startswith(prefix) and text.endswith(suffix),'Reference changes a protected boundary')
        bodies[name]=text[len(prefix):-len(suffix)]
    return bodies


def source_map(seed):
    # Only facts syntactically visible in the source, never reviewer proof paths.
    return {name:dict(includes=re.findall(r'^include "([^"]+)"',text,re.M),
        imports=[dict(alias=a,module=m,view=v or 'default') for a,m,v in
            re.findall(r'^\s*import (\w+) = (\w+)(?:`(\w+))?',text,re.M)])
        for name,text in sorted(seed.items())}


def prompt(task,seed,parser):
    rules=parser.policy(task)
    shape=json.dumps({name:'' for name in task['editable_files']})
    sections=[
        'Fill the empty Prove body in each editable file below so that all existing contracts and clients verify.',
        'Editable files: '+', '.join(task['editable_files'])+'. All other files and all declarations are immutable.',
        'Required JSON shape (replace each empty string with its proof body):\n'+shape,
        SYNTAX,
        'Concrete syntax examples:\n'+'\n'.join(SYNTAX_EXAMPLES),
        'Parameters in each editable helper: '+', '.join(rules['variables'])+'.',
        'Allowed lemma calls and argument counts: '+json.dumps(rules['calls'],sort_keys=True)+'.',
        'Allowed pure functions and argument counts: '+json.dumps(rules['pure'],sort_keys=True)+'.',
        'Only calls through the imported/exported views and the explicit lists above are allowed, even if other definitions are visible in the supplied provider sources.',
        'Declared file/include/import map (derived from the source):\n'+json.dumps(source_map(seed),indent=2),
        'Complete workspace source follows. The only edits you return are the requested body strings.',
    ]
    sections.extend('FILE '+name+'\n```dafny\n'+text+'```' for name,text in sorted(seed.items()))
    sections.append('Return the JSON object only. Every editable body must be supplied; no changes outside those bodies.')
    return '\n\n'.join(sections)+'\n'


def review_evidence():
    require(sha(SOURCE/'completion-review.json')==REVIEW_SHA,'Completion review drift')
    require(sha(SOURCE/'manifest.json')==MANIFEST_SHA,'Source manifest drift')
    require(sha(EXPERIMENT/'protocol/body_guard.py')==GUARD_SHA,'Guard drift')
    require(sha(PREVIOUS_SETTINGS)==PREVIOUS_SETTINGS_SHA,'Previous inference settings drift')
    manifest=load(SOURCE/'manifest.json')
    for name,h in manifest.items(): require(sha(SOURCE/name)==h,'Pinned source drift: '+name)
    report=load(SOURCE/'completion-review.json');counts=Counter();seen=set();rows=[]
    require(report['all_expected'] and report['final_fixture_conditions']==164,'Incomplete verifier evidence')
    checks={(c['task_id'],c['variant']):c for c in load(SOURCE/'checks.json')}
    require(len(checks)==164,'Duplicate control definitions')
    for link in report['rows']:
        identity=(link['task_id'],link['variant'])
        require(identity not in seen,'Duplicate evidence row');seen.add(identity)
        check=checks[identity];path=EXPERIMENT/link['evidence']
        require(sha(path)==link['evidence_sha256'],'Raw verifier evidence drift')
        record=load(path); expected=check['expected']
        require(record['matched'] and record['expected']==record['diagnostic']==expected,'Wrong diagnostic category')
        require(record['exit_code']==dict(success=0,proof_failure=4,termination_failure=4,resolution_failure=2)[expected],'Wrong exit code')
        require(record['attempts']==1 and record['model_calls']==0,'Unexpected verifier provenance')
        text=record['stdout']+'\n'+record['stderr']
        require('parse error' not in text.lower(),'Parse error cannot be a proof control')
        if expected=='termination_failure': require('decreases clause might not decrease' in text,'Missing termination error')
        if expected=='resolution_failure': require('unresolved identifier: Observe' in text,'Missing hidden-helper resolution error')
        if expected=='proof_failure': require('Error:' in text,'Missing proof error')
        current={n:digest(s) for n,s in files(SOURCE/check['path']).items()}
        archived={n:digest(s) for n,s in files(path.parent/check['path']).items()}
        require(current==archived==record['source_sha256']==check['source_sha256']==link['source_sha256'],'Fixture/result source mismatch')
        require('--verify-included-files' in record['command'],'Included files were not verified')
        counts[expected]+=1
        rows.append(dict(task_id=check['task_id'],variant=check['variant'],expected=expected,
            log_path=str(path.relative_to(REPO)),log_sha256=sha(path),source_sha256=current,
            job_id=link['job_id'],reused_identical_prior_result=link['reused_identical_prior_result']))
    require(seen==set(checks),'Missing reviewed control')
    require(counts==dict(success=24,proof_failure=120,termination_failure=8,resolution_failure=12),'Control coverage drift')
    parser=guard(EXPERIMENT/'protocol/body_guard.py');workloads=[]
    for task in load(SOURCE/'tasks.json'):
        seed=files(SOURCE/'fixtures'/task['task_id']/'empty')
        require({n:digest(s) for n,s in seed.items()}==task['source_sha256'],'Seed mismatch')
        reference=files(SOURCE/'fixtures'/task['task_id']/'reference')
        bodies=body_payload(parser,task,seed,reference)
        reconstructed,_=parser.parse_response(json.dumps(bodies),seed,task)
        require(reconstructed==reference,'Reference guard replay mismatch')
        workloads.append(dict(task_id=task['task_id'],semantic_instance=task['semantic_instance'],
            family=task['family'],depth=task['depth'],sharing=task['sharing'],
            source_utf8_bytes=sum(len(s.encode()) for s in seed.values()),editable_bodies=len(bodies),
            reference_body_utf8_bytes=sum(len(s.encode()) for s in bodies.values()),
            reference_bodies_identical=len(set(bodies.values()))==1,
            prompt_utf8_bytes=len(prompt(task,seed,parser).encode())))
    return dict(new_model_calls=0,new_dafny_runs=0,source_commit=SOURCE_COMMIT,
        completion_review_sha256=REVIEW_SHA,source_manifest_sha256=MANIFEST_SHA,guard_sha256=GUARD_SHA,
        selected_controls=dict(counts),reference_replays=24,controls=rows,reviewer_only_workloads=workloads,
        historical_failures_preserved=True,claims='Offline byte/evidence/reconstruction review, not new semantic or model results')


def trial_order(tasks):
    lookup={t['task_id']:t for t in tasks};ordered=[]
    for wave in range(4):
        for offset in range(6):
            index=(offset+wave)%6;instance=INSTANCES[index];cell=CELLS[ROWS[index][wave]]
            task=lookup[instance+'-'+cell.replace('_','-')]
            ordered.append(dict(trial_id=f'reasoning-cal-{len(ordered)+1:02d}',position=len(ordered)+1,
                wave=wave+1,semantic_instance=instance,family=task['family'],task_id=task['task_id'],
                cell=cell,depth=task['depth'],sharing=task['sharing'],sample=1,
                fresh_context=True,feedback=False))
    return ordered


def prepare(out):
    require(not out.exists(),'Refuse to overwrite existing freeze')
    evidence=review_evidence();tasks=load(SOURCE/'tasks.json')
    out.mkdir(parents=True,exist_ok=False);(out/'guard').mkdir();(out/'preparation').mkdir()
    for name in ['prepare.py','test_plan.py']:
        shutil.copy2(ROOT/name,out/'preparation'/name)
    shutil.copy2(EXPERIMENT/'protocol/body_guard.py',out/'guard/body_guard.py')
    shutil.copytree(SOURCE/'code',out/'verifier')
    parser=guard(out/'guard/body_guard.py')
    previous=load(PREVIOUS_SETTINGS)
    settings=dict(model_id=previous['model_id'],region=previous['region'],
        inference_config=previous['inference_config'],max_calls=24,samples_per_variant=1,
        attempts_per_trial=1,sdk_total_max_attempts=1,automatic_retries=False,reassign_unused=False,
        verify_timeout_seconds=60,dafny_version='4.11.0+fcb2042d6d043a2634f0854338c08feeaaaf4ae2',
        context='full_source_plus_declared_file_map',parser_version=parser.VERSION,parser_sha256=GUARD_SHA,
        status='FROZEN_PROPOSAL_NO_MODEL_AUTHORIZATION',model_calls_made=0,
        inference_settings_source=str(PREVIOUS_SETTINGS.relative_to(REPO)),
        inference_settings_source_sha256=PREVIOUS_SETTINGS_SHA,
        max_output_tokens_total=24*previous['inference_config']['maxTokens'])
    save(out/'settings.json',settings);save(out/'tasks.json',tasks);save(out/'evidence-review.json',evidence)
    (out/'system.txt').write_text(SYSTEM);(out/'syntax-instructions.txt').write_text(SYNTAX)
    save(out/'syntax-examples.json',SYNTAX_EXAMPLES)
    for task in tasks:
        folder=out/'tasks'/task['task_id'];folder.mkdir(parents=True)
        seed=files(SOURCE/'fixtures'/task['task_id']/'empty')
        for name,text in seed.items():(folder/name).write_text(text)
        save(folder/'declared-map.json',source_map(seed))
        user=prompt(task,seed,parser);(folder/'prompt.txt').write_text(user)
        request=dict(modelId=settings['model_id'],system=[dict(text=SYSTEM)],
            messages=[dict(role='user',content=[dict(text=user)])],inferenceConfig=settings['inference_config'])
        save(folder/'request.json',request)
    trials=trial_order(tasks)
    for trial in trials:
        path=f"tasks/{trial['task_id']}/request.json"
        trial.update(request_path=path,request_sha256=sha(out/path),
            seed_path=f"tasks/{trial['task_id']}",output_id=trial['trial_id'])
    save(out/'trials.json',trials)
    save(out/'order-design.json',dict(cells=CELLS,instance_order=INSTANCES,rows=ROWS,
        algorithm='Four waves, one request per semantic instance per wave; rotate instance order by wave index',
        first_four_rows='Four-treatment Williams square',last_two_rows='Complementary balancing permutations',
        guarantees=['Every instance visits all four cells exactly once','Each cell has six requests',
            'Each family has eight requests, two distinct instances per cell',
            'At each depth, shared appears before separate for three instances and after it for three',
            'Three instances encounter shallow first; three encounter deep first',
            'Three instances encounter shared first; three encounter separate first',
            'Each cell occupies each within-instance wave position once or twice'],
        limitations=['Six instances cannot equally fill four first-position labels',
            'Not fully balanced for every adjacent transition or exact global dispatch position',
            'Fresh contexts eliminate intended conversation carryover; temporal provider variability can remain']))
    scope=dict(status='FROZEN_PROPOSAL_NO_MODEL_AUTHORIZATION',experiment=ROOT.name,prepared_date='2026-11-02',
        proposed_max_new_calls=24,model_calls_made=0,new_dafny_runs=0,
        design='Six semantic instances x two depths x two sharing conditions x one fresh request',
        semantic_instances=6,families=3,workspace_variants=24,requests_per_variant=1,
        requests_per_instance=4,requests_per_family=8,requests_per_cell=6,
        historical_calls_reused=0,feedback=False,retries=False,reassign_unused=False,pooling_prior_model_samples=False,
        dispatch='Sequential frozen trial order, fresh output/ledger/submission, exactly one SDK attempt per reservation',
        stopping='Stop without restart/replacement on transport ambiguity, persistence failure, hash drift, verifier timeout/killing/launch failure or interrupted dispatch. Ordinary output/proof/frontend failures consume their reserved slots.',
        model_request_inputs_only=['trial.request_path'],
        reviewer_only_not_model_context=['evidence-review.json','tasks.json metadata','scope.json','order-design.json','preparation','source reference/control archives'],
        primary_metric='Strict whole-workspace exit zero with protected sources/contracts intact out of 24 planned requests; report reserved/dispatched/returned/admitted/verified denominators separately',
        secondary_metrics=['Per-instance four-cell outcomes and per-family results with two distinct instances per cell',
            'JSON/schema/guard/length or truncation failures separate from proof/precondition/postcondition/termination/frontend/infrastructure failures',
            'Tokens, response/body bytes, latency, editable-body count, exact and normalized syntax duplication; syntax is not proof identity',
            'Inspect every accepted proof and every failure, including visible-provider reuse and copying across separate bodies'],
        decision_gate=['Any output-format/guard failure requires offline review before collection scale-up; no silent repair/rescore',
            'Any task at 4/4 or 0/4 or family at 8/8 or 0/8 requires ceiling/floor review; near-ceiling and shared strategy templates also require inspection',
            'One request per variant cannot estimate sampling variability, pass@k or a causal sharing/depth effect',
            'No automatic main-corpus collection or repeat round; additional calls require a separately reviewed scope and approval'],
        token_budget=dict(max_output_tokens_per_request=4096,aggregate_output_ceiling=98304,
            input_tokens='Additional, measured by provider only during an authorized run',dollar_estimate='Not quoted; no pricing/availability probe performed'),
        future_execution_gates=['Explicit approval of 24 NEW requests bound to this freeze',
            'Separately tested/frozen bounded runner with every-dispatch deadline, durable reservation, one SDK attempt and no automatic recovery',
            'Offline real-environment package/parser tests, exact freeze and verifier version checks',
            'One compute job on live-confirmed nonpreemptible partition, no Slurm requeue or duplicate submission',
            'Inspect all existing output/ledger/job state before any action; no API connectivity test',
            'Private credential handoff only after execution approval; no key is needed for this preparation'],
        publication='Frozen request payloads, raw responses, parser decisions, guarded candidates, source hashes, verifier logs, request IDs/ledger, token usage, all failures and summaries; no secrets',
        limitations=['All six instances are inspected development tasks, not held-out or generated corpus',
            'Shared has one editable body, separate has two equivalent bodies; copying is allowed, output workload/source/imports differ',
            'Primitive implementations are visible in all contexts and remain shared in both conditions',
            'Depth is the designed reference fact path, not proved minimum proof depth',
            'The frozen guard is a bounded output language, not full Dafny; reference admission is verified but grammar rejection may restrict otherwise valid proofs',
            'No model-performance claim follows from the 164 verifier controls'])
    save(out/'scope.json',scope)
    (out/'README.md').write_text('''# Frozen 24-call proposal — execution not authorized

Six semantic instances, four matched configurations each, one fresh request each.
Only each trial's exact request.json may enter a provider request. Seed providers
and the fixed shared forwarding helper are legitimate context; reference helper
bodies, control cases, reviewer results and proof-path metadata are excluded.
The guard retains its original development version label but its exact code bytes
are frozen by SHA-256; no old parser is edited. This is preparation only: zero
model calls, no credential access, no live runner, authorization or job submission.
''')
    save(out/'freeze.json',dict(status=scope['status'],source_commit=SOURCE_COMMIT,
        proposed_calls=24,model_calls=0,files=inventory(out)))
    return out


if __name__=='__main__':print(prepare(ROOT/'frozen-001'))
