"""Body-only invariant-order revision; construction only, never a verifier run."""
import difflib
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent
spec = importlib.util.spec_from_file_location('original_stdlib_builder', PARENT / 'build.py')
original = importlib.util.module_from_spec(spec)
spec.loader.exec_module(original)
FRESH = '      invariant fresh(a.Repr - old(a.Repr))\n'
VALID = '      invariant a.Valid?()\n'
CHANGED_BODIES = {'append-reference', 'append-reverse', 'rotate-direct'}
POSITIVE_IDS = ['append-reference', 'rotate-reference']


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encode(obj):
    return (json.dumps(obj, indent=2, sort_keys=True) + '\n').encode()


def revised_body(name):
    raw = (PARENT / 'bodies' / (name + '.txt')).read_bytes()
    if name not in CHANGED_BODIES:
        return raw
    text = raw.decode()
    assert text.count(FRESH) == text.count(VALID) == 1
    assert text.index(VALID) < text.index(FRESH)
    return text.replace(FRESH, '', 1).replace(VALID, FRESH + VALID, 1).encode()


def evidence_pins():
    package = PARENT.parent
    base = package / 'qualification-002/retrieved-stdlib/qualification-002/output-stdlib'
    paths = [base / name for name in ('environment.json', 'summary.json', 'tool-version.stdout',
                                      'tool-version.stderr', 'solver-version.stdout')]
    for ident in ('baseline', 'append-reference', 'rotate-reference'):
        paths.append(base / ident / 'record.json')
        paths.extend(p for p in (base / ident / 'raw').rglob('*') if p.is_file())
    assert all(p.is_file() for p in paths)
    return {p.relative_to(package).as_posix(): sha(p.read_bytes()) for p in sorted(paths)}


def material():
    # The old builder validates all upstream Git blobs. Every old case byte is
    # also rechecked so a revision cannot silently replace its historical basis.
    old_material = original.material(PARENT)
    for name, raw in old_material.items():
        assert (PARENT / name).read_bytes() == raw, name
    old_cases = json.loads(old_material['cases.json'])
    bodies = sorted((PARENT / 'bodies').glob('*.txt'))
    files = {'bodies/' + path.name: revised_body(path.stem) for path in bodies}
    cases = []
    changes = []
    body_for_case = {row[0]: (row[2], row[3]) for row in original.specification()}
    for old in old_cases:
        if old['id'] == 'baseline':
            continue  # 56 passed old units are existing evidence, not rerun.
        case = dict(old)
        ident = case['id']
        parent_body, child_body = body_for_case[ident]
        values = {name: (PARENT / old['workspace_dir'] / name).read_bytes()
                  for name in old['source_sha256']}
        for source, template, body in ((original.APPEND, 'AppendAll.dfy', parent_body),
                                       (original.ROTATE, 'AppendRotated.dfy', child_body)):
            if body is None:
                continue
            before, after = original.fixed_parts(template, PARENT)
            value = before.encode() + revised_body(body) + after.encode()
            if value != values[source]:
                changes.append(dict(case=ident, source=source, body=body,
                                    old_sha256=sha(values[source]), new_sha256=sha(value)))
            values[source] = value
        case['source_sha256'] = {name: sha(raw) for name, raw in sorted(values.items())}
        case['source_revision'] = 'stdlib/revision-002'
        files.update({case['workspace_dir'] + '/' + name: raw for name, raw in values.items()})
        cases.append(case)
    files['cases.json'] = encode(cases)
    patch = ''.join(''.join(difflib.unified_diff(
        (PARENT / 'bodies' / (name + '.txt')).read_text().splitlines(keepends=True),
        revised_body(name).decode().splitlines(keepends=True),
        fromfile='stdlib/bodies/' + name + '.txt',
        tofile='stdlib/revision-002/bodies/' + name + '.txt'))
        for name in sorted(CHANGED_BODIES))
    files['permitted-body-diff.patch'] = patch.encode()
    inherited = ['build.py', 'cases.json', 'design.json', 'templates/AppendAll.dfy',
                 'templates/AppendRotated.dfy', 'upstream/source-manifest.json']
    inherited += ['bodies/' + p.name for p in bodies]
    inherited += ['upstream/' + name for name in original.BASE_FILES]
    revision = dict(
        schema='dafny-stdlib-invariant-order-revision-v1',
        native_status='UNKNOWN', model_calls=0, native_calls=0,
        original_job='63086889', original_observation='AppendAll correctness failed at a.Valid?() loop invariant: insufficient reads clause; Rotate correctness passed under the unproved parent contract.',
        permitted_change='Move the existing freshness invariant immediately before a.Valid?() in exactly three loop bodies; no changed statements, contracts, declarations, decreases clauses, or invariant formulas.',
        rationale='At a havoced loop head the current representation footprint may differ from the entry footprint. Freshness is the available fact that constrains newly introduced objects before checking the reads footprint of a.Valid?(). This is a proposed body repair, not a proved result.',
        changed_body_names=sorted(CHANGED_BODIES), source_changes=changes,
        unchanged_bodies=sorted(p.stem for p in bodies if p.stem not in CHANGED_BODIES),
        original_input_sha256={name: sha((PARENT / name).read_bytes()) for name in inherited},
        preserved_native_evidence_sha256=evidence_pins(),
        first_native_phase=dict(case_ids=POSITIVE_IDS, native_invocations=2,
                                baseline_repeated=False, requires_new_source_bound_inventory_review=True),
        remaining_controls=dict(case_ids=[c['id'] for c in cases if c['id'] not in POSITIVE_IDS],
                                native_invocations=9, dispatch_allowed=False,
                                gate='Both revised positive references and exact old/new native inventories must pass review first.'),
        expected_inventory=dict(baseline_passed_units=56, append_total_units=58, rotate_total_units=60,
            new_append_units=['RepoDiscoStdAppend.AppendAll (well-formedness)', 'RepoDiscoStdAppend.AppendAll (correctness)'],
            new_rotate_units=['RepoDiscoStdRotate.AppendRotated (well-formedness)', 'RepoDiscoStdRotate.AppendRotated (correctness)'],
            note='Labels/counts are observed in the preserved original run. Revised commands must report every baseline unit plus the applicable new units; a passing child does not mask failed parent correctness.'),
        model_execution_authorized=False,
    )
    files['revision.json'] = encode(revision)
    files['revision-manifest.json'] = encode(dict(
        schema='dafny-stdlib-body-revision-manifest-v1',
        files={name: sha(raw) for name, raw in sorted(files.items())},
        source_control_count=11, new_native_observations=0))
    return files


def build():
    files = material()
    for name, raw in files.items():
        path = ROOT / name
        if path.exists():
            assert path.is_file() and path.read_bytes() == raw, name
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('xb') as stream:
                stream.write(raw)
    return dict(cases=11, first_native_phase=2, gated_controls=9,
                new_native_observations=0, model_calls=0,
                cases_sha256=sha(files['cases.json']),
                manifest_sha256=sha(files['revision-manifest.json']))


if __name__ == '__main__':
    print(json.dumps(build(), indent=2, sort_keys=True))
