"""Link exact parser reconstructions to existing compute records; no new runs."""
import hashlib
import json
from pathlib import Path

import body_guard as guard

ROOT = Path(__file__).resolve().parents[1]


def load(path): return json.loads(path.read_text())
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def review():
    expected_manifest = '6838c56426de24d0a17722ca781e053e00fe46e4af70bb29e282d2d2775b9f68'
    if sha(ROOT / 'manifest.json') != expected_manifest: raise ValueError('Manifest drift')
    for name, expected in load(ROOT / 'manifest.json').items():
        if sha(ROOT / name) != sha(ROOT / 'verification-001' / name) or sha(ROOT / name) != expected:
            raise ValueError('Source/runtime drift: ' + name)
    archive = load(ROOT / 'verification-001-sha256.json')
    tasks = {task['task_id']:task for task in load(ROOT / 'tasks.json')}
    rows = []
    for check in load(ROOT / 'checks.json'):
        task = tasks[check['task_id']]
        seed = {p.name:p.read_text() for p in (ROOT / 'fixtures' / task['task_id'] / 'empty').glob('*.dfy')}
        target = {p.name:p.read_text() for p in (ROOT / check['path']).glob('*.dfy')}
        bodies = {}
        for name in task['editable_files']:
            prefix, suffix = guard.split_seed(seed[name])
            if not target[name].startswith(prefix) or not target[name].endswith(suffix): raise ValueError('Protected bytes changed')
            bodies[name] = target[name][len(prefix):-len(suffix)]
        admitted = True; rejection = None; decision = None
        try: candidate, decision = guard.parse_response(json.dumps(bodies), seed, task)
        except ValueError as error:
            admitted = False; rejection = str(error)
        if admitted:
            if candidate != target or decision['candidate_sha256'] != check['source_sha256']:
                raise ValueError('Reconstructed source differs')
        if admitted == (check['variant'] == 'hidden_shortcut'): raise ValueError('Unexpected admission result')
        rel = check['task_id'] + '-' + check['variant'] + '.json'
        record = ROOT / 'verification-001' / rel
        if sha(record) != archive[rel]: raise ValueError('Raw verifier evidence drift')
        evidence = load(record)
        if evidence['source_sha256'] != check['source_sha256'] or evidence['diagnostic'] != check['expected']:
            raise ValueError('Semantic evidence/source mismatch')
        rows.append(dict(task_id=task['task_id'], variant=check['variant'], admitted=admitted,
                         rejection=rejection, candidate_sha256=check['source_sha256'] if admitted else None,
                         compute_evidence='../verification-001/' + rel, evidence_sha256=sha(record),
                         previous_diagnostic=evidence['diagnostic'], previous_exit_code=evidence['exit_code'],
                         new_verification_performed=False))
    report = dict(policy_version=guard.VERSION, policy_sha256=sha(ROOT / 'protocol/body_guard.py'),
                  new_model_calls=0, new_verifier_invocations=0, exact_reference_replays=4,
                  exact_negative_replays=24, hidden_view_rejections=4,
                  source_manifest_sha256=expected_manifest, rows=rows,
                  interpretation='Offline byte-identical replay using prior compute evidence; no new independent trials.')
    (ROOT / 'protocol/replay-review.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({key:value for key,value in report.items() if key!='rows'},indent=2))


if __name__ == '__main__': review()
