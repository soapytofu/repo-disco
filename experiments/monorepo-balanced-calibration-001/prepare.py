"""Offline evidence review and proposal freeze. No transport or Dafny invocation."""
import collections
import hashlib
import importlib.util
import itertools
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent.parent
PARENT = ROOT.parent / 'monorepo-calibration-syntax-001' / 'frozen-001'
PARENT_SHA = 'cfa8ae517c07751f45591ce52d91c3f63240dee167f9ffbdf83b5a282799cd32'
FIXTURES = ROOT.parent / 'monorepo-calibration-v2-001'
SMOKE = ROOT.parent / 'monorepo-syntax-smoke-001'
SMOKE_REVIEW_SHA = '8708a5f3971e324e8f6086b767d1c77da89501b3bfb5b59366f0f2bbdd33e834'


def load(path):
    return json.loads(path.read_text())


def save(path, obj):
    path.write_text(json.dumps(obj, indent=2) + '\n')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def inventory(path):
    return {str(p.relative_to(path)): sha(p) for p in sorted(path.rglob('*')) if p.is_file()}


def validate_bundle(path):
    actual = inventory(path)
    actual.pop('freeze.json')
    require(actual == load(path / 'freeze.json')['files'], 'Frozen file-set/hash drift')


def sources(path):
    return {p.name: p.read_text() for p in sorted(path.glob('*.dfy'))}


def parser(bundle):
    def module(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        result = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(result)
        return result
    grammar = module('balanced_grammar', bundle / 'guard/grammar.py')
    previous = sys.modules.get('grammar')
    sys.modules['grammar'] = grammar
    try:
        body = module('balanced_body', bundle / 'guard/body_protocol.py')
    finally:
        if previous is None:
            del sys.modules['grammar']
        else:
            sys.modules['grammar'] = previous
    return grammar, body


def reference(task):
    return sources(FIXTURES / task['fixture_root'] / 'fixtures' / task['task_id'] / 'reference')


def body_texts(grammar, task, seed, candidate):
    bodies = {}
    for name in task['editable_files']:
        prefix, suffix = grammar.split_seed(seed[name])
        require(candidate[name].startswith(prefix) and candidate[name].endswith(suffix), 'Protected boundary changed')
        bodies[name] = candidate[name][len(prefix):-len(suffix)]
    return bodies


def witness_arithmetic():
    # Finite illustration only, not a substitute for the archived Dafny proofs.
    valid = wrong = 0
    for a, b, c, d in itertools.product(range(-3, 4), repeat=4):
        if a <= b and c <= d and a <= d and c <= b:
            valid += 1
            wrong += not (a <= c <= b and c <= c <= d)
            w = c if a <= c else a
            require(a <= w <= b and c <= w <= d, 'Witness explanation is inconsistent')
    return dict(domain='All integer a,b,c,d in [-3,3]', admissible_quadruples=valid,
                unconditional_c_failures=wrong, branched_witness_failures=0,
                example=dict(a=2, b=5, c=0, d=4),
                limitation='Finite arithmetic illustration; no model repair, rescoring or new Dafny run')


def review_evidence():
    require(sha(PARENT / 'freeze.json') == PARENT_SHA, 'Wrong clarified prompt parent')
    validate_bundle(PARENT)
    require(sha(SMOKE / 'results-review.json') == SMOKE_REVIEW_SHA, 'Smoke review changed')
    raw = inventory(SMOKE / 'model-001')
    require(raw == load(SMOKE / 'model-001-sha256.json'), 'Historical smoke archive changed')
    grammar, body = parser(PARENT)
    tasks = load(PARENT / 'tasks.json')
    gates = {g['task_id']: g for g in load(PARENT / 'preflight-gate.json')}
    counts = collections.Counter()
    pins = {}
    rows = []
    for task in tasks:
        seed = sources(PARENT / 'tasks' / task['task_id'])
        require({n: digest(s) for n, s in seed.items()} == task['source_sha256'], 'Seed changed')
        gate = gates[task['task_id']]
        require(gate['selected_controls_all_expected'], 'Unvalidated task')
        require(sha(REPO / gate['review_path']) == gate['review_sha256'], 'Prior review changed')
        pins[gate['review_path']] = gate['review_sha256']
        require(len(gate['evidence']) == gate['control_count'], 'Control count changed')
        for evidence in gate['evidence']:
            path = REPO / evidence['log_path']
            require(sha(path) == evidence['log_sha256'], 'Prior verifier log changed')
            pins[evidence['log_path']] = evidence['log_sha256']
            log = load(path)
            require(log['source_sha256'] == evidence['source_sha256'], 'Verifier source hashes changed')
            expected = evidence['expected']
            require(log['exit_code'] == {'success': 0, 'proof_failure': 4,
                    'termination_failure': 4, 'resolution_failure': 2}[expected], 'Wrong verifier category')
            if expected == 'termination_failure':
                require('decreases clause might not decrease' in log['stdout'], 'Missing termination diagnostic')
            elif expected == 'resolution_failure':
                require('unresolved identifier: Direct' in log['stdout'], 'Wrong hidden-helper diagnostic')
            elif expected == 'proof_failure':
                require(log['category'] == 'proof_failure' and 'Error:' in log['stdout'], 'Not a proof failure')
            if evidence['variant'] == 'empty':
                require(evidence['source_sha256'] == task['source_sha256'], 'Empty control does not bind seed')
            counts[expected] += 1
        ref = reference(task)
        bodies = body_texts(grammar, task, seed, ref)
        candidate, _ = body.parse_response(json.dumps(bodies), seed, task)
        ref_gate = next(e for e in gate['evidence'] if e['variant'] == 'reference')
        require(candidate == ref and {n: digest(s) for n, s in ref.items()} == ref_gate['source_sha256'],
                'Reference reconstruction changed')
        rows.append(dict(task_id=task['task_id'], family=task['family'], depth=task['depth'],
            sharing=task['sharing'], seed_utf8_bytes=sum(len(s.encode()) for s in seed.values()),
            prompt_utf8_bytes=len((PARENT / 'tasks' / task['task_id'] / 'prompt.txt').read_bytes()),
            editable_body_count=len(bodies), reference_body_utf8_bytes=sum(len(b.encode()) for b in bodies.values()),
            reference_identical_editable_bodies=len(set(bodies.values())) == 1,
            reference_depth=task.get('reference_depth', task.get('reference_contract_application_chain')),
            prior_reference_log=ref_gate['log_path']))
    require(dict(counts) == dict(success=16, proof_failure=108, termination_failure=4, resolution_failure=8),
            'Expected selected control coverage changed')
    smoke_rows = []
    for old in load(SMOKE / 'results-review.json')['trials']:
        folder = SMOKE / 'model-001' / old['trial_id']
        trial = load(folder / 'trial.json')
        task = next(t for t in tasks if t['task_id'] == trial['task_id'])
        seed = sources(PARENT / 'tasks' / task['task_id'])
        response = load(folder / 'response.json')
        candidate, extraction = body.parse_response(response['text'], seed, task)
        require(candidate == sources(folder / 'candidate'), 'Historical candidate replay differs')
        require(load(folder / 'extraction.json') == dict(accepted=True, **extraction), 'Historical extraction differs')
        verification = load(folder / 'verification.json')
        require(verification['source_sha256'] == {n: digest(s) for n, s in candidate.items()}, 'Historical verification bytes differ')
        require(verification['exit_code'] == old['verifier_exit'], 'Historical score changed')
        bodies = body_texts(grammar, task, seed, candidate)
        smoke_rows.append(dict(trial_id=old['trial_id'], task_id=task['task_id'], outcome=old['outcome'],
            verifier_exit=verification['exit_code'], editable_bodies_identical=len(set(bodies.values())) == 1,
            verification_path=str((folder / 'verification.json').relative_to(REPO)),
            response_sha256=sha(folder / 'response.json'), verification_sha256=sha(folder / 'verification.json')))
    require([r['trial_id'] for r in smoke_rows if r['verifier_exit'] != 0] == ['smoke-04'], 'Smoke outcome drift')
    return dict(model_calls=0, new_dafny_runs=0, parent_freeze_sha256=PARENT_SHA,
                selected_prior_controls=dict(counts), prior_evidence_sha256=pins,
                reference_replays=len(rows), task_workloads=rows,
                smoke_archive_file_count=len(raw), smoke_inventory_sha256=sha(SMOKE / 'model-001-sha256.json'),
                smoke_review_sha256=SMOKE_REVIEW_SHA, smoke_replays=smoke_rows,
                witness_arithmetic=witness_arithmetic(),
                claims='Offline integrity/replay and finite arithmetic checks only; historical model outcomes unchanged')


def prepare(out):
    require(not out.exists(), 'Refuse to overwrite existing freeze')
    review = review_evidence()
    out.mkdir(parents=True, exist_ok=False)
    for name in ['tasks', 'guard']:
        shutil.copytree(PARENT / name, out / name)
    for name in ['system.txt', 'settings.json', 'tasks.json', 'order-design.json', 'preflight-gate.json']:
        shutil.copy2(PARENT / name, out / name)
    trials = []
    for previous in load(PARENT / 'trials.json'):
        trials.append(dict(previous, trial_id=previous['trial_id'].replace('trial-', 'balanced-'),
                           source_trial_id=previous['trial_id']))
    save(out / 'trials.json', trials)
    save(out / 'evidence-review.json', review)
    (out / 'difficulty-review.md').write_bytes((ROOT / 'DIFFICULTY_REVIEW.md').read_bytes())
    scope = dict(status='FROZEN_PROPOSAL_NO_MODEL_AUTHORIZATION', experiment='monorepo-balanced-calibration-001',
        model_calls_made=0, proposed_max_new_calls=32, historical_calls_reused=0,
        parent_freeze_sha256=PARENT_SHA, prompts_sources_parser_settings_changed=False,
        design='Four development families x two depths x two sharing conditions x two fresh samples',
        semantic_instances=4, workspace_variants=16, per_variant_requests=2, per_family_requests=8,
        attempts_per_sample=1, sdk_total_max_attempts=1, automatic_retries=False, reassign_unused=False,
        fresh_context=True, feedback=False, resume_existing_runs=False, pooling_with_prior_runs=False,
        order='Exact parent order: four cyclic Latin rows, interleaved families; complete reversal for sample two',
        order_limit='Balances positions, not all ordered transitions; midpoint repeats one variant in fresh contexts',
        primary_metric='Strict whole-workspace exit zero AND intact guarded source/contracts out of planned 32; report reserved/dispatched/completed separately',
        secondary_metrics=['Parser/guard admission; JSON/schema/body/edit rejection categories',
            'Proof precondition/postcondition/assertion/termination, frontend, timeout and infrastructure categories',
            'Per-family four-cell results (2 samples per cell), with repeats grouped under variant and semantic instance',
            'Tokens, bytes, editable-body count, latency, and identical/normalized body reuse; not independent task counts'],
        stopping_rule='Stop on transport ambiguity, hash drift, persistence or verifier infrastructure failure; no automatic retry, restart or replacement. Ordinary output/proof failures consume their slots.',
        review_gate=dict(protocol='Any output-format/guard failure blocks main scale-up for offline diagnosis; never silently repair/rescore',
            difficulty='Family 0/8 or 8/8 requires floor/ceiling inspection before scale-up; any near-ceiling or trivial reusable template also needs review',
            matching='Check invariant client targets, shared-vs-separate workload, reference-relative depth and shortcut controls',
            analysis='Inspect all failures and proof strategy/duplicates for every success; distinguish difficulty from format',
            no_automatic_expansion='Even a successful calibration does not authorize the 192-call main corpus'),
        output_token_ceiling=32 * load(PARENT / 'settings.json')['inference_config']['maxTokens'],
        cost_note='Output-token cap only; input tokens additional. No price or expected-use claim.',
        model_message_inputs_only=['system.txt', 'trial.prompt_path'],
        reviewer_only_not_model_context=['evidence-review.json', 'difficulty-review.md', 'preflight-gate.json', 'scope.json'],
        future_execution_gates=['Explicit new 32-call authorization bound to this scope and separately tested/frozen runner',
            'Fake-transport and real-environment offline tests; every-dispatch budget/deadline and durable reservation',
            'Fresh output/ledger/submission state check; one job on live-confirmed nonpreemptible compute; no requeue',
            'No model connectivity tests; credential handoff only for later authorized execution'],
        publication='Exact frozen messages, raw responses, ledger/request IDs, guarded candidates, verifier stdout/stderr, hashes, all failures and summary; no secrets',
        limitations=['Development calibration, one semantic instance per family; no held-out or population claim',
            'Shared one helper vs separate two equivalent helper bodies changes output workload; copying is allowed',
            'Provider implementations are visible trusted context; this is API-contract composition, not from-scratch provider synthesis',
            'Reference depth is not proved minimal; all mathematical Kernel/provider definitions remain shared',
            'Fresh requests are new samples of already inspected problems, not independent new semantic tasks',
            'Old scores remain 18/32, 1/32 and smoke 7/8; no causal prompt-effect claim'])
    save(out / 'scope.json', scope)
    (out / 'README.md').write_text('# Balanced calibration freeze: preparation only\n\n32 proposed fresh requests; zero authorized or made. Prompt/source/parser/settings\nbytes and order are inherited exactly from the clarified syntax bundle. Trial IDs\nare new and scoped to this experiment. Reviewer-only files must never enter model\nmessages. No live dispatcher, authorization, credentials or job is included.\n')
    save(out / 'freeze.json', dict(status=scope['status'], trial_count=32, model_calls=0, files=inventory(out)))
    return out


if __name__ == '__main__':
    print(prepare(ROOT / 'frozen-001'))
