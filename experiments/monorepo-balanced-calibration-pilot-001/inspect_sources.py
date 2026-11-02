"""Post-run offline source/strategy audit. No requests or verifier processes."""
import collections
import hashlib
import json
from pathlib import Path
import run_pilot as r

ROOT = Path(__file__).resolve().parent


def main():
    r.validate_bundle()
    r.validate_runtime()
    guard = r.guard_module(ROOT)
    rows, syntaxes = [], set()
    for trial in r.load(ROOT / 'results-review.json')['trials']:
        folder = ROOT / 'model-001' / trial['trial_id']
        task = r.load(folder / 'task.json')
        seed = {n: b.decode() for n, b in r.sources(ROOT, task).items()}
        candidate = {p.name: p.read_text() for p in (folder / 'candidate').glob('*.dfy')}
        extraction = r.load(folder / 'extraction.json')
        refroot = ROOT.parent / 'monorepo-calibration-v2-001' / task['fixture_root'] / 'fixtures' / task['task_id'] / 'reference'
        ref = {p.name: p.read_text() for p in refroot.glob('*.dfy')}
        bodyrows = []
        for name in task['editable_files']:
            prefix, suffix = guard.split_seed(seed[name])
            body = candidate[name][len(prefix):-len(suffix)]
            if candidate[name] != prefix + body + suffix:
                raise ValueError('Protected boundary changed')
            refbody = ref[name][len(prefix):-len(suffix)]
            tree = extraction['syntax_trees'][name]
            if guard.Grammar(body, task).sequence() != tree:
                raise ValueError('Saved syntax tree changed')
            ref_tree = guard.Grammar(refbody, task).sequence()
            digest = hashlib.sha256(json.dumps(tree, sort_keys=True).encode()).hexdigest()
            syntaxes.add(digest)
            bodyrows.append(dict(file=name, utf8_bytes=len(body.encode()), syntax_sha256=digest,
                                 reference_syntax_match=tree == ref_tree))
        if set(candidate) != set(seed) or any(candidate[n] != s for n, s in seed.items() if n not in task['editable_files']):
            raise ValueError('Protected source changed')
        rows.append(dict(trial_id=trial['trial_id'], task_id=task['task_id'], outcome=trial['outcome'],
                         bodies=bodyrows, identical_separate_bodies=len(bodyrows) == 2 and bodyrows[0]['syntax_sha256'] == bodyrows[1]['syntax_sha256'],
                         protected_source_intact=True))
    groups = collections.defaultdict(list)
    for row in rows:
        groups[row['task_id']].append(tuple(body['syntax_sha256'] for body in row['bodies']))
    report = dict(new_model_calls=0, new_dafny_runs=0, all_protected_sources_intact=True,
                  trials=rows, distinct_normalized_body_syntax=len(syntaxes),
                  separate_trials=sum(len(row['bodies']) == 2 for row in rows),
                  separate_identical_bodies=sum(row['identical_separate_bodies'] for row in rows),
                  repeated_variant_syntax_matches=sum(len(group) == 2 and group[0] == group[1] for group in groups.values()),
                  repeated_variants=len(groups),
                  note='Fingerprints compare body syntax ignoring whitespace, not algebraic equivalence or repository-scoped proof identity. Repetition is not independent semantic evidence; no cross-repository reuse claim.')
    (ROOT / 'source-review.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'trials'}, indent=2))


if __name__ == '__main__':
    main()
