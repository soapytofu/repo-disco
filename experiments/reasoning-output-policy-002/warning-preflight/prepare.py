"""Prepare one explicit analyst-authored alias substitution, never a model call."""
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parent
POLICY = ROOT.parent
PILOT = POLICY.parent / 'monorepo-reasoning-calibration-pilot-001'
DIAGNOSTIC = POLICY.parent / 'reasoning-response-diagnostic-001'
sys.path.insert(0, str(POLICY))
from body_guard import parse_response, digest


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def load(path): return json.loads(path.read_text())
def save(path, data):
    with path.open('x') as handle: handle.write(json.dumps(data, indent=2) + '\n')
def require(condition):
    if not condition: raise ValueError('Pinned input mismatch')


def main():
    policy_freeze = load(POLICY / 'validation-freeze.json')
    for name, expected in policy_freeze['files'].items(): require(sha(POLICY / name) == expected)
    task = next(t for t in load(PILOT / 'frozen-001/tasks.json') if t['task_id'] == 'commuting_updates-shallow-shared')
    response = PILOT / 'model-001/reasoning-cal-24/response.json'
    old_record = DIAGNOSTIC / 'verification-001/reasoning-cal-24-unaltered-body.json'
    require(sha(old_record) == '054f8673e1283bb1c186aad8644168611d437431cce8689a248221e3d429ca72')
    prior = load(old_record)
    require(prior['case']['original_response_sha256'] == sha(response))
    require(prior['evidence']['exit_code'] == 2)
    bodies = json.loads(load(response)['text'])
    require(set(bodies) == {'HelperA.dfy'})
    original = bodies['HelperA.dfy']
    marker = '    forall q |'
    require(original.count(marker) == 2)
    prefix, tail = original.split(marker, 1)
    tail = marker + tail
    changes = [('m[k := x][j := y]', 'lhs'), ('m[j := y][k := x]', 'rhs')]
    replacements = []
    for old, new in changes:
        count = tail.count(old)
        require(count > 0)
        tail = tail.replace(old, new)
        replacements.append(dict(old=old, new=new, occurrences=count))
    changed = prefix + tail
    seed = {p.name: p.read_text() for p in (PILOT / 'frozen-001/tasks' / task['task_id']).glob('*.dfy')}
    candidate, decision = parse_response(json.dumps({'HelperA.dfy': changed}), seed, task)
    for name in set(seed) - {'HelperA.dfy'}: require(candidate[name] == seed[name])
    for directory, sources in [('seed', seed), ('candidate', candidate)]:
        folder = ROOT / directory
        folder.mkdir(exist_ok=False)
        for name, text in sources.items():
            with (folder / name).open('x') as handle: handle.write(text)
    save(ROOT / 'task.json', task)
    save(ROOT / 'original-body.json', bodies)
    save(ROOT / 'analyst-body.json', {'HelperA.dfy': changed})
    save(ROOT / 'guard-decision.json', decision)
    save(ROOT / 'mutation.json', dict(original_trial='reasoning-cal-24', analyst_authored=True,
         original_response_sha256=sha(response), original_body_sha256=digest(original),
         changed_body_sha256=digest(changed), original_warning_evidence_sha256=sha(old_record),
         replacements=replacements, prefix_before_first_forall_unchanged=True,
         purpose='Test whether existing lhs/rhs aliases permit trigger inference without attributes or relaxing warnings.',
         added_lemma_calls=0, source_contracts_unchanged=True, policy_freeze_sha256=sha(POLICY / 'validation-freeze.json'),
         original_pilot_score='18/24 unchanged', new_model_calls=0))
    code = ROOT / 'code'
    code.mkdir(exist_ok=False)
    for source in (DIAGNOSTIC / 'code').rglob('*.py'):
        dest = code / source.relative_to(DIAGNOSTIC / 'code')
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest)
    shutil.copy2(POLICY / 'body_guard.py', code / 'body_guard.py')
    print(json.dumps(dict(prepared_cases=1, candidate_files=len(candidate), replacements=replacements,
                          new_model_calls=0, new_verifier_invocations=0)))


if __name__ == '__main__': main()
