"""Build source-bound analyst controls offline; never invokes a verifier."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
UPSTREAM = REPO / 'experiments/real-repository-qualification-001/upstream/dafny-vmc'
SOURCE_MANIFEST = REPO / 'experiments/real-repository-qualification-001/source-manifest.json'
BEGIN = '    // BEGIN MODEL BODY\n'
END = '    // END MODEL BODY\n'
DESTINATIONS = {
    'move': 'repodisco-growth/MoveToFront.dfy',
    'pair': 'repodisco-growth/PickPair.dfy',
    'detached': 'repodisco-growth/Detached.dfy',
}
CASES = [
    ('move-reference', 'move-reference', None, 'PASS', False),
    ('move-alternative', 'move-alternative', None, 'PASS', False),
    ('move-noop', 'move-noop', None, 'MOVE_PROOF_FAILURE', False),
    ('move-endpoint-swap', 'move-endpoint-swap', None, 'MOVE_PROOF_FAILURE', False),
    ('pair-reference', 'move-reference', 'pair-reference', 'PASS', False),
    ('pair-alternative', 'move-reference', 'pair-alternative', 'PASS', False),
    ('pair-noop', 'move-reference', 'pair-noop', 'PAIR_PROOF_FAILURE', False),
    ('pair-first-only', 'move-reference', 'pair-first-only', 'PAIR_PROOF_FAILURE', False),
    ('pair-wrong-adjustment', 'move-reference', 'pair-wrong-adjustment', 'PAIR_PROOF_FAILURE', False),
    ('pair-with-unproved-parent', 'move-noop', 'pair-reference', 'MOVE_PROOF_FAILURE_CLIENT_MAY_PASS', False),
    ('detached-explicit', 'move-reference', 'pair-reference', 'DETACHED_PROOF_FAILURE', True),
    ('detached-omitted', 'move-reference', 'pair-reference', 'NATIVE_PASS_COVERAGE_REJECT', True),
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def render(kind, body_id):
    name = 'MoveToFront.dfy' if kind == 'move' else 'PickPair.dfy'
    template = (ROOT / 'templates' / name).read_text()
    if template.count(BEGIN) != 1 or template.count(END) != 1:
        raise ValueError('Ambiguous body boundary')
    prefix, suffix = template.split(BEGIN)[0] + BEGIN, template.split(END)[1]
    body = (ROOT / 'bodies' / (body_id + '.txt')).read_text()
    return (prefix + ''.join('    ' + line + '\n' for line in body.splitlines()) + END + suffix).encode()


def save_exact(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError('Existing control differs: ' + str(path))
        return
    with path.open('xb') as stream:
        stream.write(data)


def build():
    source = next(x for x in json.loads(SOURCE_MANIFEST.read_bytes()) if x['id'] == 'dafny-vmc')
    for name, expected in source['files'].items():
        if sha((UPSTREAM / name).read_bytes()) != expected:
            raise ValueError('Pinned upstream changed: ' + name)
    records = []
    for case_id, move_body, pair_body, expected, detached in CASES:
        candidate_files = {DESTINATIONS['move']: render('move', move_body)}
        if pair_body:
            candidate_files[DESTINATIONS['pair']] = render('pair', pair_body)
        if detached:
            candidate_files[DESTINATIONS['detached']] = (ROOT / 'controls/Detached.dfy').read_bytes()
        for name, data in candidate_files.items():
            save_exact(ROOT / 'fixtures' / case_id / name, data)
        records.append(dict(
            id=case_id, expected=expected,
            additions={name: sha(data) for name, data in candidate_files.items()},
            explicitly_omit_from_command=[DESTINATIONS['detached']] if case_id == 'detached-omitted' else [],
            required_units=[
                'FisherYates.GrowthShift.MoveToFront (well-formedness)',
                *(['FisherYates.GrowthPick.PickPair (well-formedness)'] if pair_body else []),
                *(['QualificationGrowthDetached.Fails (correctness)'] if detached else []),
            ],
        ))
    inventory = dict(
        status='OFFLINE_CONSTRUCTED_NOT_DAFNY_VERIFIED', model_calls=0, native_verifier_calls=0,
        upstream_repository=source['repository'], upstream_commit=source['commit'],
        upstream_source_manifest_sha256=sha(SOURCE_MANIFEST.read_bytes()),
        unchanged_upstream_files=len(source['files']), cases=records,
        required_upstream_units=267,
        unit_labels_are_expected_until_confirmed_by_native_csv=True,
        staging='Overlay exactly these additions on the immutable pinned upstream source. Native file arguments remain host-owned.',
    )
    save_exact(ROOT / 'controls-manifest.json', (json.dumps(inventory, indent=2, sort_keys=True) + '\n').encode())
    return inventory


if __name__ == '__main__':
    result = build()
    print(json.dumps({k: v for k, v in result.items() if k != 'cases'}, indent=2))
    print('Constructed controls:', len(result['cases']))
