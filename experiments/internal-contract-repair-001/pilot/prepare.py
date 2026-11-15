"""Deterministic, offline-only prompt preparation. No execution or provider client."""
from collections import Counter
from pathlib import Path, PurePosixPath
import argparse
import base64
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
REPO = STUDY.parents[1]
SOURCE_COMMIT = '00ac8039418f60963c8ac2499c48187dc447e1ae'
PLAN_SHA256 = '899c180bffbb7ea0c91601c7700a496442f5360ff4bd1ecba344cd131c0e969f'
GATE_SHA256 = '51c3281392be1f2850ed8752e48b166cacfc9b34e493c6ff149bda017897cd37'
INDEPENDENT_SHA256 = 'f076638e4bf5f1b89b82442dabd3b7a940b58b904837a02149c72f58b61bebe8'
POLICY_SHA256 = 'c6fdae216ad20a7291391c64dbdf60c17cdbc4f956d0b5afe7c6de138872fe6a'
MEASUREMENT_SHA256 = '02e6f053757c057503da7464de8677c4728d9a031746cb880d0849fcb1733e5a'
FILES = ['All.dfy', 'Client.dfy', 'Helper.dfy', 'Kernel.dfy']
EDITABLE = ['Helper.dfy', 'Client.dfy']
ARMS = ['verifier_diagnostics', 'failure_notice_only']
OPEN = '<verifier_feedback>\n'
CLOSE = '\n</verifier_feedback>'
NOTICE = 'The supplied workspace did not verify.'
RESULT_LINE = re.compile(rb'Results File: /tmp/repodisco-repair-adapter-[A-Za-z0-9_-]+/TestResults/[^\r\n]+(?:\r?\n)?')


def sha(raw): return hashlib.sha256(raw).hexdigest()
def file_sha(path): return sha(Path(path).read_bytes())
def encode(value): return (json.dumps(value, indent=2, ensure_ascii=False) + '\n').encode('utf-8')
def unique(pairs):
    result = {}
    for k, v in pairs:
        if k in result: raise ValueError('Duplicate JSON key')
        result[k] = v
    return result
def read(path): return json.loads(Path(path).read_bytes(), object_pairs_hook=unique)
def require(ok, message):
    if not ok: raise ValueError(message)
def safe(root, name):
    relative = PurePosixPath(name)
    require(relative.parts and not relative.is_absolute() and '..' not in relative.parts, 'Unsafe relative input')
    root = Path(root).resolve(); path = root / str(relative)
    require(path.resolve().is_relative_to(root), 'Input escaped root')
    for ancestor in (path, *path.parents):
        if ancestor == root: break
        require(not ancestor.is_symlink(), 'Symlink input')
    require(path.is_file(), 'Missing regular input: ' + str(path))
    return path


def validate_plan(plan):
    require(plan['study'] == 'internal-contract-repair-001' and plan['proposed_model_requests'] == 16, 'Wrong proposed scope')
    require(plan['unique_payloads'] == 4 and plan['unique_semantic_instances'] == 2, 'Wrong task/payload count')
    require(plan['responses_per_task_arm'] == 4 and plan['max_requests_per_trial'] == 1, 'Wrong replication/attempt count')
    require(plan['feedback_conditions'] == ARMS and len(plan['task_ids']) == 2, 'Wrong conditions')
    require(plan['new_context_per_request'] and plan['fixed_target_internal_api'], 'Wrong repair setting')
    require(not any(plan[n] for n in ('execution_authorized', 'automatic_retries', 'reassign_unused', 'slurm_requeue',
                                    'feedback_after_repair', 'model_contract_editing', 'helper_call_required')), 'Unapproved execution or changed design')
    require(plan['editable_files'] == EDITABLE and plan['editable_targets'] == ['Helper.Transfer', 'Client.Target'], 'Wrong edit scope')
    require(plan['model_id'] == 'global.anthropic.claude-opus-4-5-20251101-v1:0'
            and plan['region'] == 'us-east-1'
            and plan['inference_config'] == {'temperature': 1.0, 'maxTokens': 4096}, 'Settings changed')
    order = plan['order']; require(len(order) == 16, 'Wrong order length')
    require([s['position'] for s in order] == list(range(1, 17)), 'Order positions changed')
    cells = {(tid, arm) for tid in plan['task_ids'] for arm in ARMS}
    observed = [(s['task_id'], s['feedback_condition']) for s in order]
    require(Counter(observed) == Counter({cell: 4 for cell in cells}), 'Unbalanced cells')
    for i in range(4):
        require(set(observed[i * 4:(i + 1) * 4]) == cells, 'Unbalanced replicate block')
        require(all(s['replicate_block'] == i + 1 for s in order[i * 4:(i + 1) * 4]), 'Block index changed')
    require(all(sum(s['position'] for s in order if (s['task_id'], s['feedback_condition']) == cell) == 34
                for cell in cells), 'Position means differ')


def source_inputs():
    """Validate reviewed local evidence and return a pin inventory, without rerunning it."""
    pins = {}
    def pin(path, expected=None):
        path = Path(path); require(path.resolve().is_relative_to(REPO.resolve()), 'Input outside repository')
        raw = safe(REPO, str(path.relative_to(REPO))).read_bytes(); digest = sha(raw)
        require(expected is None or digest == expected, 'Input pin differs: ' + str(path))
        pins[str(path.relative_to(REPO))] = digest
        return raw
    plan = json.loads(pin(STUDY / 'plan.json', PLAN_SHA256)); validate_plan(plan)
    gate = json.loads(pin(STUDY / 'reviews/seed-review-001/stdout.json', GATE_SHA256))
    independent = json.loads(pin(STUDY / 'reviews/seed-review-001/independent-review.json', INDEPENDENT_SHA256))
    require(gate['all_expected'] and gate['job_id'] == '60865223' and gate['new_verifier_checks'] == 2
            and gate['reused_observations'] == 8 and gate['new_model_calls'] == 0 and not gate['execution_authorized'], 'Seed gate incomplete')
    require(independent['gate_sha256'] == GATE_SHA256
            and independent['verdict'] == 'ready_for_four_payload_prompt_preparation', 'Independent seed review missing')
    require(len(gate['fresh_checks']) == 2 and len(gate['reused_checks']) == 8, 'Incomplete review records')
    pin(STUDY / 'review_seed_evidence.py', gate['review_code_sha256'])
    policy = json.loads(pin(STUDY / 'protocol/policy-manifest.json', POLICY_SHA256))
    measurement = json.loads(pin(STUDY / 'measurement/measurement-manifest.json', MEASUREMENT_SHA256))
    require(measurement['guard_policy_manifest_sha256'] == POLICY_SHA256, 'Measurement/policy mismatch')
    require(policy['policy_id'] == 'internal-contract-method-bodies-v1-development', 'Wrong method policy')
    for manifest_path, digest in gate['pinned_bundles'].items():
        manifest = json.loads(pin(STUDY / manifest_path, digest))
        if manifest_path.startswith('protocol/'):
            entries = manifest['files']
        elif manifest_path.startswith('measurement/'):
            entries = manifest['files_sha256']
        else:
            entries = manifest
        base = (STUDY / manifest_path).parent
        for name, file_digest in entries.items(): pin(safe(base, name), file_digest)
    # Every exact archived seed input and raw result is pinned. None is automatically rendered.
    archive = STUDY / 'fixtures-and-controls/verification-001'
    for path in sorted(archive.rglob('*')):
        require(not path.is_symlink(), 'Archive symlink')
        if path.is_file(): pin(path)
    for name in ('prepare.py', 'test_plan.py', 'system.txt', 'syntax.txt', 'README.md'):
        pin(HERE / name)
    tasks = json.loads(pin(STUDY / 'fixtures-and-controls/tasks.json', policy['source_tasks_sha256']))
    require([t['task_id'] for t in tasks] == plan['task_ids'], 'Task order differs')
    fresh = {r['case_id']: r for r in gate['fresh_checks']}
    records = {}
    for task in tasks:
        require(task['semantic_instance'] == next(s['semantic_instance'] for s in plan['order'] if s['task_id'] == task['task_id']), 'Semantic instance changed')
        require(task['editable_files'] == EDITABLE and task['internal_api_version'] == 'new_fixed_before_repair', 'Target API changed')
        case_id = task['task_id'] + '-seed'; row = fresh[case_id]
        record_path = archive / (case_id + '.json')
        record = json.loads(pin(record_path, row['record_sha256']))
        require(record['case_id'] == case_id and record['source_sha256'] == task['source_sha256'] == row['source_sha256'], 'Seed source/evidence mismatch')
        require(record['exit_code'] == 4 and record['attempts'] == 1 and record['model_calls'] == 0
                and not record['timed_out'] and record['execution_error'] is None, 'Seed execution failed')
        require(row['outcome'] == 'PROOF_FAILURE'
                and row['named_evidence']['local_targets'] == {'Helper.Transfer': False, 'Client.Target': False}, 'Real two-method failures required')
        for name in FILES:
            raw = pin(safe(STUDY / 'fixtures-and-controls', task['path'] + '/' + name), task['source_sha256'][name])
            require(raw == safe(archive, task['path'] + '/' + name).read_bytes(), 'Archived seed differs')
        for stream in ('stdout', 'stderr'):
            raw = pin(archive / 'raw' / case_id / (stream + '.txt'), record[stream + '_sha256'])
            require(raw == base64.b64decode(record[stream + '_base64'], validate=True)
                    and raw.decode('utf-8') == record[stream]
                    and sha(raw) == row['raw_sha256'][stream + '.txt'], 'Exact stream differs')
        for name, digest in record['csv_sha256'].items():
            raw = pin(safe(archive / 'raw' / case_id / 'csv', name), digest)
            require(raw == base64.b64decode(record['csv_base64'][name], validate=True)
                    and raw.decode('utf-8') == record['csv'][name]
                    and sha(raw) == row['raw_sha256']['csv/' + name], 'Exact CSV differs')
        records[task['task_id']] = record
    return plan, tasks, records, gate, policy, measurement, pins


def feedback(record):
    raw = base64.b64decode(record['stdout_base64'], validate=True)
    require(sha(raw) == record['stdout_sha256'] and raw.decode('utf-8') == record['stdout'], 'Original stdout mismatch')
    lines = raw.splitlines(keepends=True)
    positions = [i for i, line in enumerate(lines) if line.startswith(b'Results File: ')]
    require(len(positions) == 1 and RESULT_LINE.fullmatch(lines[positions[0]]), 'Expected one temporary Results File line')
    index = positions[0]; transformed = b''.join(line for i, line in enumerate(lines) if i != index)
    stderr = base64.b64decode(record['stderr_base64'], validate=True)
    require(sha(stderr) == record['stderr_sha256'] and stderr.decode('utf-8') == record['stderr'], 'Original stderr mismatch')
    clean = {'exit_code': record['exit_code'], 'stdout': transformed.decode('utf-8'), 'stderr': stderr.decode('utf-8')}
    audit = {'transformation': 'remove_exactly_one_complete_Results_File_temporary_path_line_from_stdout_only',
             'stdout_original_sha256': sha(raw), 'stdout_transformed_sha256': sha(transformed),
             'stderr_original_and_transformed_sha256': sha(stderr),
             'removed_line_index_zero_based': index, 'removed_line_base64': base64.b64encode(lines[index]).decode('ascii'),
             'removed_line_sha256': sha(lines[index]), 'all_other_bytes_unchanged': True}
    return clean, audit


def visible_environment(task):
    result = {}
    for filename in EDITABLE:
        rules = task['file_rules'][filename]
        result[filename] = {
            'read_only_inputs': [{'name': n, 'type': rules['parameter_types'][n]} for n in rules['variables']],
            'return_variables': rules['output_types'],
            'returning_methods': {n: {'arguments': rules['call_types'][n], 'result': rules['call_returns'][n]} for n in rules['calls']},
            'pure_functions': rules['pure_types'],
        }
    return result


def render(task, sources, diagnostic, syntax_text):
    """Visible-data whitelist: no task/case IDs, control metadata or analyst repairs."""
    require(sorted(sources) == FILES, 'Exact source membership required')
    parts = [
        'The supplied workspace failed verification. Repair the bodies of Helper.Transfer and Client.Target so the entire workspace verifies.',
        'Every byte outside those two method bodies is fixed. Keep the supplied current Helper.Transfer interface and every public Client.Target contract exactly as shown; do not change any requires, ensures, parameters, return declarations, imports or names. All.dfy and Kernel.dfy are immutable. Return both body strings; either may be unchanged.',
        'Permitted syntax:\n' + syntax_text,
        'Per-file typed symbol environments:\n' + json.dumps(visible_environment(task), indent=2),
        'Use only the symbols permitted for that body. Calling H.Transfer is permitted but not required.',
    ]
    for filename in FILES:
        parts.append('FILE ' + filename + '\n```dafny\n' + sources[filename] + '```')
    parts.extend([OPEN + diagnostic + CLOSE,
                  'Return only one JSON object with the two complete replacement body strings, keyed Helper.dfy and Client.dfy.'])
    return '\n\n'.join(parts) + '\n'


def without_feedback(text):
    require(text.count(OPEN) == text.count(CLOSE) == 1, 'Feedback delimiters ambiguous')
    before, rest = text.split(OPEN); _, after = rest.split(CLOSE)
    return before + OPEN + '<feedback omitted>' + CLOSE + after


def contents():
    plan, tasks, records, gate, policy, measurement, pins = source_inputs()
    output = {}; requests = {}; parents = {}; pairs = []
    system = (HERE / 'system.txt').read_text(); syntax_text = (HERE / 'syntax.txt').read_text()
    output['source-plan.json'] = (STUDY / 'plan.json').read_bytes()
    output['seed-gate.json'] = (STUDY / 'reviews/seed-review-001/stdout.json').read_bytes()
    output['independent-seed-review.json'] = (STUDY / 'reviews/seed-review-001/independent-review.json').read_bytes()
    output['policy-manifest.json'] = (STUDY / 'protocol/policy-manifest.json').read_bytes()
    output['measurement-manifest.json'] = (STUDY / 'measurement/measurement-manifest.json').read_bytes()
    output['system.txt'] = system.encode(); output['syntax.txt'] = syntax_text.encode()
    for name in policy['runtime_files_sha256']:
        output['policy/' + name] = safe(STUDY / 'protocol', name).read_bytes()
    binding_keys = list(read(STUDY / 'protocol/registry.json')['tasks'][tasks[0]['task_id']]['binding'])
    for index, task in enumerate(tasks, 1):
        workspace_id = 'workspace-' + str(index).zfill(2)
        sources = {n: safe(STUDY / 'fixtures-and-controls', task['path'] + '/' + n).read_bytes().decode('utf-8') for n in FILES}
        base = 'parents/' + workspace_id
        for name in FILES: output[base + '/base/' + name] = sources[name].encode()
        output[base + '/task.json'] = encode({key: task[key] for key in binding_keys})
        record = records[task['task_id']]; cleaned, transformation = feedback(record)
        case_id = task['task_id'] + '-seed'
        record_path = STUDY / 'fixtures-and-controls/verification-001' / (case_id + '.json')
        output[base + '/verification.json'] = record_path.read_bytes()
        for stream in ('stdout', 'stderr'):
            output[base + '/raw/' + stream + '.txt'] = base64.b64decode(record[stream + '_base64'], validate=True)
        for name, raw in record['csv_base64'].items():
            output[base + '/raw/csv/' + name] = base64.b64decode(raw, validate=True)
        output[base + '/feedback.json'] = encode(cleaned)
        output[base + '/feedback-transformation.json'] = encode(transformation)
        parents[task['task_id']] = {'task_id': task['task_id'], 'semantic_instance': task['semantic_instance'],
            'workspace_id': workspace_id, 'task_path': base + '/task.json', 'base_path': base + '/base',
            'source_sha256': task['source_sha256'], 'verification_path': base + '/verification.json',
            'verification_sha256': file_sha(record_path), 'feedback_path': base + '/feedback.json'}
        texts = {}
        for arm in ARMS:
            label = 'diagnostics' if arm == ARMS[0] else 'notice'
            text = render(task, sources, json.dumps(cleaned, indent=2) if arm == ARMS[0] else NOTICE, syntax_text)
            payload = {'modelId': plan['model_id'], 'system': [{'text': system}],
                       'messages': [{'role': 'user', 'content': [{'text': text}]}],
                       'inferenceConfig': plan['inference_config']}
            path = 'requests/' + workspace_id + '-' + label + '.json'
            output[path] = encode(payload); requests[(task['task_id'], arm)] = path; texts[arm] = text
            output['prompts/' + workspace_id + '-' + label + '.txt'] = ('SYSTEM\n' + system + '\nUSER\n' + text).encode()
        require(without_feedback(texts[ARMS[0]]) == without_feedback(texts[ARMS[1]]), 'Non-feedback paired difference')
        pairs.append({'task_id': task['task_id'], 'only_feedback_differs': True,
                      'source_sha256': task['source_sha256'], 'common_prompt_sha256': sha(without_feedback(texts[ARMS[0]]).encode())})
    trials = []
    for slot in plan['order']:
        path = requests[(slot['task_id'], slot['feedback_condition'])]
        trials.append({**slot, 'trial_id': 'internal-contract-repair-' + str(slot['position']).zfill(2),
                       'request_path': path, 'request_sha256': sha(output[path]), 'max_calls': 1})
    settings = {'api_shape': 'bedrock.converse', 'model_id': plan['model_id'], 'region': plan['region'],
                'inference_config': plan['inference_config'], 'sdk_total_max_attempts_if_executed': 1,
                'new_context_per_request': True, 'max_requests_per_trial': 1, 'feedback_after_repair': False,
                'automatic_retries': False, 'reassign_unused': False, 'slurm_requeue': False}
    scope = {'schema': 'internal-contract-repair-frozen-proposal-v1', 'study': plan['study'],
             'status': 'FROZEN_NOT_AUTHORIZED', 'proposed_model_requests': 16, 'execution_authorized': False,
             'new_model_calls_during_preparation': 0, 'new_verifier_runs_during_preparation': 0,
             'unique_semantic_instances': 2, 'unique_payloads': 4, 'responses_per_task_arm': 4,
             'source_evidence_commit': SOURCE_COMMIT, 'historical_design_source_commit': plan['source_commit'],
             'historical_design_plan_sha256': PLAN_SHA256, 'seed_gate_sha256': GATE_SHA256,
             'policy_manifest_sha256': POLICY_SHA256, 'measurement_manifest_sha256': MEASUREMENT_SHA256,
             'primary_outcome': plan['primary_outcome'], 'secondary_descriptive_fields': plan['secondary_descriptive_fields'],
             'fixed_target_internal_api': True, 'model_contract_editing': False, 'helper_call_required': False,
             'max_output_tokens_if_all_16_execute': 16 * plan['inference_config']['maxTokens'],
             'budget_note': plan['budget_note'], 'limits': plan['limits']}
    for name, value in [('parents.json', parents), ('order.json', trials), ('settings.json', settings), ('scope.json', scope),
                        ('prompt-pairs.json', pairs)]: output[name] = encode(value)
    return output, pins


def build(out):
    out = Path(out).resolve()
    require(out.is_relative_to(HERE.resolve()) and out != HERE.resolve(), 'Output must be a new child of pilot/')
    output, pins = contents()
    require(not out.exists(), 'Never overwrite an existing freeze')
    out.mkdir(parents=False)
    for name, raw in output.items():
        path = out / name; path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream: stream.write(raw)
    freeze = {'schema': 'internal-contract-repair-prompt-freeze-v1', 'study': 'internal-contract-repair-001',
              'proposed_model_requests': 16, 'unique_payloads': 4, 'execution_authorized': False,
              'model_requests_during_preparation': 0, 'source_evidence_commit': SOURCE_COMMIT,
              'files': {name: sha(raw) for name, raw in sorted(output.items())},
              'repository_inputs_sha256': dict(sorted(pins.items()))}
    (out / 'freeze.json').write_bytes(encode(freeze))
    return check(out)


def check(out):
    out = Path(out); freeze = read(out / 'freeze.json')
    require(freeze['schema'] == 'internal-contract-repair-prompt-freeze-v1'
            and freeze['proposed_model_requests'] == 16 and not freeze['execution_authorized'], 'Freeze scope drift')
    actual = set()
    for p in out.rglob('*'):
        require(not p.is_symlink(), 'Freeze symlink')
        if p.is_file(): actual.add(str(p.relative_to(out)))
    require(actual == set(freeze['files']) | {'freeze.json'}, 'Freeze file inventory differs')
    for name, digest in freeze['files'].items(): require(file_sha(safe(out, name)) == digest, 'Frozen bytes changed: ' + name)
    for name, digest in freeze['repository_inputs_sha256'].items(): require(file_sha(safe(REPO, name)) == digest, 'Source input changed: ' + name)
    expected, pins = contents()
    require(pins == freeze['repository_inputs_sha256'], 'Input inventory changed')
    require({name: sha(raw) for name, raw in sorted(expected.items())} == freeze['files'], 'Frozen rendering differs')
    require(freeze['source_evidence_commit'] == SOURCE_COMMIT, 'Source provenance differs')
    return {'freeze_sha256': file_sha(out / 'freeze.json'), 'frozen_files': len(expected),
            'repository_inputs': len(pins), 'payloads': 4, 'proposed_slots': 16,
            'execution_authorized': False, 'model_calls': 0, 'verifier_runs': 0}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('action', choices=('build', 'check'))
    parser.add_argument('--out', type=Path, default=HERE / 'frozen-001')
    args = parser.parse_args()
    print(json.dumps(build(args.out) if args.action == 'build' else check(args.out), indent=2))
