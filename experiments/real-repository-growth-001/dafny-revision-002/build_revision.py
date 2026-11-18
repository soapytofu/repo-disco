"""Namespace-only source revision after preserved native resolution failure.

Offline construction only. Never executes a verifier or changes prior inputs.
"""
import copy
import difflib
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent / 'dafny'
REPO = ROOT.parents[2]
UPSTREAM = REPO / 'experiments/real-repository-qualification-001/upstream/dafny-vmc'
SOURCE_MANIFEST = REPO / 'experiments/real-repository-qualification-001/source-manifest.json'
FAILURE = ROOT.parent / 'qualification-001/verification-dafny-vmc-001/pair-reference'
HEADERS = {
    'MoveToFront.dfy': (
        ('module FisherYates.GrowthShift {\n', 'module RepoDiscoGrowthShift {\n'),
        ('  import Model\n', '  import Model = FisherYates.Model\n'),
    ),
    'PickPair.dfy': (
        ('module FisherYates.GrowthPick {\n', 'module RepoDiscoGrowthPick {\n'),
        ('  import Shift = FisherYates.GrowthShift`Public\n',
         '  import Shift = RepoDiscoGrowthShift`Public\n'),
    ),
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def save_exact(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != raw:
            raise ValueError('Existing revision artifact differs: ' + str(path))
        return
    with path.open('xb') as stream:
        stream.write(raw)


def json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()


def rewrite(name, old):
    """Allow exactly lines 2 and 3 of the two extension files to change."""
    if name == 'Detached.dfy':
        return old, []
    if name not in HEADERS:
        raise ValueError('Unrecognized revision source: ' + name)
    lines = old.decode('utf-8').splitlines(keepends=True)
    changes = []
    for index, (before, after) in zip((1, 2), HEADERS[name]):
        if lines[index] != before:
            raise ValueError('Expected namespace/import header differs: ' + name)
        lines[index] = after
        changes.append(dict(line=index + 1, before=before, after=after))
    new = ''.join(lines).encode()
    assert new.splitlines(keepends=True)[3:] == old.splitlines(keepends=True)[3:]
    assert new.splitlines(keepends=True)[0] == old.splitlines(keepends=True)[0]
    return new, changes


def build():
    parent_index = read(PARENT / 'offline-files-001.json')['files']
    for name, value in parent_index.items():
        if sha((PARENT / name).read_bytes()) != value:
            raise ValueError('Frozen parent source changed: ' + name)
    upstream = next(x for x in read(SOURCE_MANIFEST) if x['id'] == 'dafny-vmc')
    for name, value in upstream['files'].items():
        raw = (UPSTREAM / name).read_bytes()
        if sha(raw) != value:
            raise ValueError('Protected upstream changed: ' + name)
        if b'RepoDiscoGrowthShift' in raw or b'RepoDiscoGrowthPick' in raw:
            raise ValueError('New top-level module name already appears upstream: ' + name)
    observed = read(FAILURE / 'observation.json')
    if observed['category'] != 'RESOLUTION_OR_TYPE_FAILURE' or observed['proof_pass']:
        raise ValueError('Parent failure outcome differs')
    if read(FAILURE / 'record.json')['exit_code'] != 2:
        raise ValueError('Parent failure exit differs')
    stdout = (FAILURE / 'stdout.txt').read_text()
    cycle = 'module FisherYates -> module GrowthPick -> import Shift -> module FisherYates'
    if cycle not in stdout:
        raise ValueError('Expected parent namespace-cycle diagnostic missing')

    parent = read(PARENT / 'controls-manifest.json')
    records = []
    provenance = {}
    diff_parts = []

    def convert(relative):
        before = (PARENT / relative).read_bytes()
        after, edits = rewrite(Path(relative).name, before)
        save_exact(ROOT / relative, after)
        provenance[relative] = dict(parent_path=(PARENT / relative).relative_to(REPO).as_posix(),
            parent_sha256=sha(before), revision_sha256=sha(after), permitted_edits=edits,
            all_bytes_except_listed_header_lines_unchanged=True,
            suffix_after_line_3_sha256=sha(b''.join(before.splitlines(keepends=True)[3:])))
        diff_parts.extend(difflib.unified_diff(before.decode().splitlines(keepends=True),
            after.decode().splitlines(keepends=True), fromfile='dafny/' + relative,
            tofile='dafny-revision-002/' + relative, n=2))
        return after

    for entry in parent['cases']:
        revised = copy.deepcopy(entry)
        revised['additions'] = {}
        for path in entry['additions']:
            relative = 'fixtures/' + entry['id'] + '/' + path
            revised['additions'][path] = sha(convert(relative))
        revised['required_units'] = [u.replace('FisherYates.GrowthShift.', 'RepoDiscoGrowthShift.')
                                     .replace('FisherYates.GrowthPick.', 'RepoDiscoGrowthPick.')
                                     for u in entry['required_units']]
        records.append(revised)
    for name in ('MoveToFront.dfy', 'PickPair.dfy'):
        convert('templates/' + name)

    inventory = {**parent, 'status': 'OFFLINE_NAMESPACE_REVISION_NOT_NATIVE_VERIFIED',
        'cases': records, 'parent_controls_manifest_sha256': sha((PARENT / 'controls-manifest.json').read_bytes()),
        'parent_offline_files_sha256': sha((PARENT / 'offline-files-001.json').read_bytes()),
        'revision': '002', 'reason': 'Remove the added enclosing-FisherYates import cycle without changing proof text.',
        'model_calls': 0, 'native_verifier_calls': 0,
        'prior_native_observation': dict(job_id='61747428', exit_code=2,
             category='RESOLUTION_OR_TYPE_FAILURE', proof_gate_passed=False),
        'staging': 'Overlay these versioned additions on the same immutable upstream; do not overwrite the original frozen qualification.'}
    save_exact(ROOT / 'controls-manifest.json', json_bytes(inventory))
    save_exact(ROOT / 'source-provenance.json', json_bytes(provenance))
    save_exact(ROOT / 'allowed-source-diffs.patch', ''.join(diff_parts).encode())
    evidence_names = ['stdout.txt', 'stderr.txt', 'record.json', 'profile.json',
                      'bound-record.json', 'source-after.json', 'observation.json']
    evidence = {n: sha((FAILURE / n).read_bytes()) for n in evidence_names}
    design = dict(status='OFFLINE_NAMESPACE_REVISION_NATIVE_CHECK_PENDING', model_calls=0,
        native_verifier_calls=0, revision='002', controls=12,
        upstream_commit=upstream['commit'], protected_upstream_files=len(upstream['files']),
        required_original_unit_count=267,
        parent_failure=dict(job_id='61747428', category=observed['category'], exit_code=2,
            diagnostic_cycle=cycle, path=FAILURE.relative_to(REPO).as_posix(), raw_evidence_sha256=evidence),
        stages=[dict(destination='repodisco-growth/MoveToFront.dfy', module='RepoDiscoGrowthShift',
                     import_binding='Model = FisherYates.Model', target='MoveToFront'),
                dict(destination='repodisco-growth/PickPair.dfy', module='RepoDiscoGrowthPick',
                     import_binding='Shift = RepoDiscoGrowthShift`Public', target='PickPair')],
        reasoning=[
            'The original added GrowthPick is a FisherYates child; its qualified sibling import traverses the parent that implicitly depends on that child.',
            'Both revised additions are distinct top-level modules, outside the existing FisherYates parent.',
            'Stage one explicitly binds its unchanged Model alias to the original FisherYates.Model; stage two binds its unchanged Shift alias to the top-level stage-one Public export.',
            'No protected upstream source refers to either new name, so these additions introduce no upstream-to-growth back edge.',
            'This is namespace/dependency reasoning, not a successful native resolution or proof observation.'
        ],
        preservation=dict(contracts=True, bodies=True, decreases=True, export_visibility=True,
                          call_arguments=True, destinations=True, expected_control_outcomes=True,
                          omission_controls=True, original_sources=True, original_failure=True),
        new_unit_labels_provisional_until_native_csv=True,
        no_native_execution_or_submission_prepared=True)
    save_exact(ROOT / 'design.json', json_bytes(design))
    return inventory


if __name__ == '__main__':
    result = build()
    print(json.dumps(dict(status=result['status'], controls=len(result['cases']),
                         protected_upstream_files=result['unchanged_upstream_files'],
                         model_calls=0, native_verifier_calls=0), indent=2))
