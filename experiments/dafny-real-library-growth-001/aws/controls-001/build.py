"""Construct exactly nine offline AWS controls from unchanged draft inputs."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import re

ROOT = Path(__file__).resolve().parent
AWS = ROOT.parent
PACKAGE = AWS.parent
STAGE1 = 'StandardLibrary/src/RepoDiscoU16Frame.dfy'
STAGE2 = 'AwsCryptographicMaterialProviders/dafny/AwsCryptographicMaterialProviders/src/RepoDiscoContextEntry.dfy'
PARENT_TARGET = 'RepoDiscoU16Frame.ReadU16Frame'
CHILD_TARGET = 'RepoDiscoContextEntry.ReadContextEntry'
REFERENCE_IDS = {0: 'aws-baseline-001', 1: 'aws-stage1-reference-001', 2: 'aws-stage2-reference-001'}
BAD_BODY_IDS = ('stage1-always-failure', 'stage1-wrong-suffix', 'stage1-wrong-payload',
                'stage2-always-failure', 'stage2-swapped-fields', 'stage2-wrong-suffix',
                'stage2-no-utf8-check')
CONTROL_IDS = BAD_BODY_IDS + ('unproved-parent-passing-child', 'stage2-omitted-from-roots')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encode(value):
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()


def checked(path):
    path = Path(path)
    assert path.is_file() and not path.is_symlink(), str(path)
    return path.read_bytes()


def source_hashes(sources):
    return {name: sha(raw) for name, raw in sorted(sources.items())}


def reference(stage):
    ident = REFERENCE_IDS[stage]
    metadata = json.loads(checked(AWS / 'cases-001' / ident / 'case.json'))
    assert metadata['id'] == ident
    assert metadata['workspace'] == 'cases-001/' + ident + '/workspace'
    folder = AWS / metadata['workspace']
    sources = {}
    for item in metadata['source_files']:
        name = item['path']
        assert not PurePosixPath(name).is_absolute() and '..' not in PurePosixPath(name).parts
        assert name.endswith('.dfy') and name not in sources
        raw = checked(folder / name)
        assert len(raw) == item['bytes'] and sha(raw) == item['sha256'], name
        if item['origin'] == 'pinned-upstream':
            assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == item['git_blob_sha'], name
        sources[name] = raw
    actual = {p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file()}
    assert actual == set(sources)
    assert len(metadata['explicit_root_files']) == len(set(metadata['explicit_root_files']))
    assert set(metadata['explicit_root_files']) == set(sources)
    assert len(sources) == 102 + stage
    return metadata, sources


def fixed_parts(raw, target):
    """Exact known last-function boundary, not a general Dafny parser."""
    name = target.split('.')[-1]
    declaration = ('  function method {:opaque} ' + name + '(').encode()
    assert raw.count(declaration) == 1
    start = raw.index(b'\n  {\n', raw.index(declaration)) + len(b'\n  {\n')
    suffix = b'  }\n}\n\n'
    assert raw.endswith(suffix)
    return raw[:start], suffix


def include_closure(roots, sources):
    """Check the literal include graph of these already pinned source files."""
    pending, visited = list(roots), set()
    while pending:
        name = pending.pop()
        if name in visited:
            continue
        assert name in sources, name
        visited.add(name)
        for relative in re.findall(r'^\s*include\s+"([^"\r\n]+)"', sources[name].decode(), re.M):
            parts = list(PurePosixPath(name).parent.parts)
            for part in PurePosixPath(relative).parts:
                if part == '..':
                    assert parts, (name, relative)
                    parts.pop()
                elif part != '.':
                    parts.append(part)
            pending.append('/'.join(parts))
    return visited


def material():
    source_manifest = json.loads(checked(AWS / 'cases-001/manifest.json'))
    draft = json.loads(checked(AWS / 'draft/controls.json'))
    declared = {c['id']: c for c in draft['cases']}
    assert len(declared) == len(draft['cases']) == 11
    assert set(declared) - {'stage1-reference', 'stage2-reference'} == set(CONTROL_IDS)
    assert draft['positive_gate_first'] is True
    assert draft['target_paths'] == dict(stage1=STAGE1, stage2=STAGE2)
    refs = {stage: reference(stage) for stage in (0, 1, 2)}
    baseline = refs[0][1]
    assert all(refs[stage][1][name] == raw for stage in (1, 2) for name, raw in baseline.items())
    assert refs[1][1][STAGE1] == refs[2][1][STAGE1] == checked(AWS / 'draft/overlay' / STAGE1)
    assert refs[2][1][STAGE2] == checked(AWS / 'draft/overlay' / STAGE2)
    assert source_manifest['cases'] == [refs[stage][0] for stage in (0, 1, 2)]
    config_path = PACKAGE / 'qualification-002/configs/aws.json'
    config = json.loads(checked(config_path))
    assert config['project'] == 'aws' and config['source_pin'] == 'dab800a2a610253659d113ee6e4bf8a70b86d13a'
    prefix = [config['dafny'], 'verify'] + config['options']
    files, cases = {}, []
    inputs = {'cases-001/manifest.json', 'draft/controls.json',
              'draft/overlay/' + STAGE1, 'draft/overlay/' + STAGE2}
    inputs.update('cases-001/' + ident + '/case.json' for ident in REFERENCE_IDS.values())
    for ident in CONTROL_IDS:
        row = declared[ident]
        stage = 1 if ident.startswith('stage1-') else 2
        meta, inherited = refs[stage]
        sources, replacements = dict(inherited), {}
        if ident in BAD_BODY_IDS:
            path = STAGE1 if stage == 1 else STAGE2
            replacement = row['file']
            sources[path] = checked(AWS / replacement)
            replacements[path] = replacement
        elif ident == 'unproved-parent-passing-child':
            replacement = row['sources']['stage1']
            sources[STAGE1] = checked(AWS / replacement)
            replacements[STAGE1] = replacement
            assert row['sources']['stage2'] == 'draft/overlay/' + STAGE2
        else:
            assert ident == 'stage2-omitted-from-roots'
            assert row['expected'] == 'COVERAGE_REJECTION'
        for path, source in replacements.items():
            inputs.add(source)
            target = PARENT_TARGET if path == STAGE1 else CHILD_TARGET
            before, after = fixed_parts(inherited[path], target)
            assert sources[path].startswith(before) and sources[path].endswith(after), ident
            assert sources[path] != inherited[path], ident
        omitted = [STAGE2] if ident == 'stage2-omitted-from-roots' else []
        command_files = [name for name in meta['explicit_root_files'] if name not in omitted]
        assert include_closure(command_files, sources) == set(sources) - set(omitted)
        bad_parent = stage == 1 or ident == 'unproved-parent-passing-child'
        failed = [] if omitted else [PARENT_TARGET if bad_parent else CHILD_TARGET]
        passed = [PARENT_TARGET] if stage == 2 and not bad_parent else []
        expected = 'COVERAGE_OMISSION' if omitted else 'PROOF_FAILURE'
        workspace = 'cases/' + ident + '/workspace'
        files.update({workspace + '/' + name: raw for name, raw in sources.items()})
        cases.append(dict(
            id=ident, workspace_dir=workspace, stage=stage,
            command_files=command_files, declared_scope_files=meta['explicit_root_files'],
            argv=prefix + command_files, source_sha256=source_hashes(sources),
            expected_category=expected, expected_native_category='PROOF_PASS' if omitted else 'PROOF_FAILURE',
            expected_failed_targets=failed, expected_passed_targets=passed,
            required_targets=[PARENT_TARGET] + ([CHILD_TARGET] if stage == 2 else []),
            omitted_targets=[CHILD_TARGET] if omitted else [], omit_from_command=omitted,
            omitted_source_all_units=omitted,
            inspect_targets=[CHILD_TARGET] if ident == 'unproved-parent-passing-child' else [],
            child_outcome_predetermined=False if ident == 'unproved-parent-passing-child' else None,
            expected_native_scope='stage1' if stage == 1 or omitted else 'stage1+stage2',
            source_reference_case=meta['id'], draft_control_id=ident,
            replacement_inputs={path:dict(aws_relative_path=source, sha256=sha(sources[path]))
                                for path, source in replacements.items()},
            native_status='UNKNOWN', actual_native_unit_labels=None,
            native_dispatch_allowed=False, positive_qualification_gate_required=True,
            classification_requires_named_units_and_exact_inventory=True,
            upstream_unit_policy='Every qualified unchanged upstream unit must be present and pass; no frontend, timeout, resource, or missing-result substitute for the named failure.',
            analyst_authored=True, model_acceptance=False))
    files['cases.json'] = encode(cases)
    inherited_pins = {'aws/' + name:sha(checked(AWS / name)) for name in sorted(inputs)}
    inherited_pins['qualification-002/configs/aws.json'] = sha(checked(config_path))
    files['plan.json'] = encode(dict(
        schema='repodisco-aws-negative-controls-v1', status='PREPARED_GATED_NATIVE_UNKNOWN',
        case_ids=list(CONTROL_IDS), expected_counts=dict(bad_body=7, unproved_parent=1, omitted_root=1),
        excluded_completed_or_running_reference_cases=list(REFERENCE_IDS.values()),
        native_dispatch_allowed=False, model_execution_authorized=False, native_calls=0, model_calls=0,
        gate='Root must review successful AWS baseline and both reference inventories before submitting these distinct controls. No automatic dispatch/retry.',
        upstream_source_count=102, unchanged_upstream_sha256=source_hashes(baseline),
        fixed_reference_sources={STAGE1:sha(refs[1][1][STAGE1]),STAGE2:sha(refs[2][1][STAGE2])},
        command_policy=dict(qualified_config='qualification-002/configs/aws.json',
                            command_prefix=prefix, wall_seconds=config['wall_seconds'],
                            toolchain_version=config['expected_version'],
                            no_resource_escalation=True),
        inherited_inputs_sha256=inherited_pins,
        scope_limit='Dependency-closed selected 102-source AWS/library component, not the full AWS repository.',
        inherited_trust='All pre-existing extern/axiom/spec definitions and their exact source bytes remain unchanged; native inventories and explicit unlogged-definition treatment remain qualification gates.',
        unproved_parent_note='The historical control ID mentions passing-child, but the exact child outcome is observed, not prescribed. Parent target must genuinely fail; a child pass under that unproved contract is never workspace acceptance.',
        omission_note='The stage-two reference file remains staged and hashed. Only its explicit argv entry is removed, and include-closure checks show it is not reached. Expected native stage-one success must still be rejected for missing every stage-two obligation.',
    ))
    files['manifest.json'] = encode(dict(schema='repodisco-aws-controls-source-manifest-v1',
        files={name:sha(raw) for name, raw in sorted(files.items())},
        cases=9, native_status='UNKNOWN', model_calls=0))
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
    return dict(cases=9, source_files=sum(name.endswith('.dfy') for name in files),
                cases_sha256=sha(files['cases.json']), manifest_sha256=sha(files['manifest.json']),
                native_calls=0, model_calls=0, native_dispatch_allowed=False)


if __name__ == '__main__':
    print(json.dumps(build(), indent=2, sort_keys=True))
