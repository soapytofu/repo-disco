"""Rebuild or validate an offline freeze. No provider, scheduler or verifier access."""
import argparse
from collections import Counter
from pathlib import Path
import json
import runpy
import tempfile

HERE = Path(__file__).resolve().parent
EXP = HERE.parent
REPO = EXP.parent
TASK = EXP / 'conditional-monotonicity-001'
POLICY = EXP / 'monorepo-policy-integration-001'
PREVIOUS = EXP / 'monorepo-reasoning-calibration-001'
# The earlier preparation has side-effect-free helpers for the declared source map,
# exact editable spans, JSON serialization and SHA-256 inventories.
common = runpy.run_path(str(PREVIOUS / 'prepare.py'))
load, save, sha = (common[k] for k in ('load', 'save', 'sha'))
require, inventory = (common[k] for k in ('require', 'inventory'))
SEED_FILES = {'All.dfy', 'Api.dfy', 'ClientA.dfy', 'ClientB.dfy', 'HelperA.dfy',
              'HelperB.dfy', 'Kernel.dfy', 'Ops1.dfy', 'Ops2.dfy'}
CELLS = {d + '-' + s for d in ('shallow', 'deep') for s in ('shared', 'separate')}


def validate_design(plan):
    blocks = plan['blocks']
    require(len(blocks) == 2 and all(len(b) == 4 and set(b) == CELLS for b in blocks),
            'Each block must include each cell once')
    order = blocks[0] + blocks[1]
    require(all(a != b for a, b in zip(order, order[1:])), 'Adjacent repetition')
    for first, second in zip(*blocks):
        require(all(a != b for a, b in zip(first.split('-'), second.split('-'))),
                'Block positions must counterbalance both factors')
    require(len(order) == plan['proposed_calls'] == 8 and plan['samples_per_workspace'] == 2,
            'Trial count drift')
    require(plan['fresh_context_per_request'] and plan['sdk_total_max_attempts'] == 1
            and not any(plan[k] for k in ('feedback', 'reassign_unused', 'slurm_requeue', 'execution_authorized')),
            'Proposal or request limits changed')


def user_text(task, seeds, rules):
    editable = task['editable_files']
    parts = [
        'Complete the empty Prove bodies so the entire workspace verifies.',
        'Required response keys and shape: ' + json.dumps(dict.fromkeys(editable, '')),
        (HERE / 'syntax.txt').read_text().strip(),
        'Parameters: ' + ', '.join(rules['variables']),
        'Allowed lemma calls (argument counts): ' + json.dumps(rules['calls'], sort_keys=True),
        'Allowed pure functions (argument counts): ' + json.dumps(rules['pure'], sort_keys=True),
        'Declared include/import map:\n' + json.dumps(common['source_map'](seeds), indent=2),
    ]
    parts.extend(f'FILE {name}\n```dafny\n{text}```' for name, text in sorted(seeds.items()))
    return '\n\n'.join(parts) + '\n'


def build(out):
    plan = load(HERE / 'plan.json')
    validate_design(plan)
    baseline = load(PREVIOUS / 'frozen-001/settings.json')
    for key in ('model_id', 'inference_config', 'region'):
        require(plan[key] == baseline[key], 'Inference setting drift: ' + key)
    require(plan['max_output_tokens_total'] == 8 * plan['inference_config']['maxTokens'], 'Token cap drift')
    env = load(TASK / 'verification-001/environment.json')
    require((env['dafny'], env['z3']) == (plan['verifier']['toolchain'], plan['verifier']['z3']), 'Toolchain drift')
    parser_path = POLICY / 'body_guard.py'
    require(sha(parser_path) == load(POLICY / 'validation-freeze.json')['files']['body_guard.py'], 'Guard drift')
    guard = common['guard'](parser_path)
    require(guard.VERSION == plan['guard_version'], 'Guard version mismatch')
    tasks = load(TASK / 'tasks.json')
    catalog = {r['task_id']: r for r in load(POLICY / 'task-catalog.json')['tasks']}
    evidence = load(TASK / 'verification-001-review.json')
    require(evidence['all_expected'] and evidence['planned'] == evidence['matched'] == 32
            and Counter(r['diagnostic'] for r in evidence['rows']) ==
            {'success': 4, 'proof_failure': 24, 'resolution_failure': 4}, 'Control review incomplete')
    input_files = [HERE / name for name in ('prepare.py', 'syntax.txt', 'plan.json', 'README.md')]
    input_files += [parser_path, POLICY / 'validation-freeze.json', POLICY / 'task-catalog.json',
                    TASK / 'tasks.json', TASK / 'verification-001-review.json', TASK / 'verification-001/environment.json',
                    PREVIOUS / 'prepare.py', PREVIOUS / 'frozen-001/system.txt', PREVIOUS / 'frozen-001/settings.json']
    input_files += sorted((TASK / 'code').rglob('*.py'))
    system = (PREVIOUS / 'frozen-001/system.txt').read_text()
    out.mkdir(exist_ok=False)
    (out / 'requests').mkdir()
    paths = {}
    for task in tasks:
        cell = task['depth'] + '-' + task['sharing']
        require(task['semantic_instance'] == plan['semantic_instance'] and cell not in paths, 'Unexpected task')
        name = task['task_id']
        entry = catalog[name]
        folder = TASK / 'fixtures' / name
        seed_dir = folder / 'empty'
        require(REPO / entry['seed_path'] == seed_dir, 'Catalog source path drift')
        seeds = common['files'](seed_dir)
        require(set(seeds) == SEED_FILES and inventory(seed_dir) == task['source_sha256'] == entry['seed_sha256'],
                'Workspace drift: ' + name)
        rules = guard.policy(task)
        require(rules == dict(variables=entry['variables'], calls=entry['lemma_calls'], pure=entry['pure_functions'])
                and task['editable_files'] == entry['editable_files'], 'Registry mismatch: ' + name)
        # Replay archived positive controls offline. Only empty seeds go into the request.
        reference = common['files'](folder / 'reference')
        bodies = common['body_payload'](guard, task, seeds, reference)
        candidate, decision = guard.parse_response(json.dumps(bodies), seeds, task)
        record_path = TASK / 'verification-001' / (name + '-reference.json')
        record = load(record_path)
        require(candidate == reference and record['source_sha256'] == decision['candidate_sha256']
                and record['matched'] and record['diagnostic'] == 'success' and record['exit_code'] == 0
                and '--verify-included-files' in record['command'], 'Reference replay mismatch: ' + name)
        require(set(bodies) == ({'HelperA.dfy'} if task['sharing'] == 'shared' else {'HelperA.dfy', 'HelperB.dfy'}),
                'Editable set drift')
        input_files.extend(sorted(seed_dir.glob('*.dfy')))
        input_files.extend(sorted((folder / 'reference').glob('*.dfy')))
        input_files.append(record_path)
        request = dict(modelId=plan['model_id'], system=[dict(text=system)],
                       messages=[dict(role='user', content=[dict(text=user_text(task, seeds, rules))])],
                       inferenceConfig=plan['inference_config'])
        paths[cell] = 'requests/' + cell + '.json'
        save(out / paths[cell], request)

    require(set(paths) == CELLS, 'Missing workspace')
    trials = []
    for block, cells in enumerate(plan['blocks'], 1):
        for cell in cells:
            path = paths[cell]
            trials.append(dict(trial_id=f'monotone-{len(trials)+1:02d}', sample=block,
                               task_id=plan['semantic_instance'] + '-' + cell,
                               request_path=path, request_sha256=sha(out / path)))
    save(out / 'trials.json', trials)
    save(out / 'freeze.json', dict(base_commit=plan['base_commit'], proposed_calls=8, execution_authorized=False,
                                  files=inventory(out), repository_inputs_sha256={
                                      str(p.relative_to(REPO)): sha(p) for p in sorted(input_files)}))


if __name__ == '__main__':
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument('--write', type=Path, help='Create a new freeze directory; refuses overwrite')
    output = args.parse_args().write
    if output is not None:
        build(output)
    else:
        with tempfile.TemporaryDirectory() as tmp:
            rebuilt = Path(tmp) / 'rebuilt'
            build(rebuilt)
            require(inventory(rebuilt) == inventory(HERE / 'frozen-001'), 'Published freeze drift')
        print('PASS: exact freeze rebuild, eight slots, balanced order, four reference/seed/guard replays.')
