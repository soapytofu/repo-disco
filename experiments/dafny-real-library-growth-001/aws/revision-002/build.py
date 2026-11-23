"""Construct the new closed UInt/raw-frame-pair development component offline."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import re

ROOT = Path(__file__).resolve().parent
AWS = ROOT.parent
PACKAGE = AWS.parent
BASE = ['StandardLibrary/src/UInt.dfy', 'libraries/src/BoundedInts.dfy', 'libraries/src/Wrappers.dfy']
STAGE1 = 'StandardLibrary/src/RepoDiscoU16Frame.dfy'
STAGE2 = 'StandardLibrary/src/RepoDiscoFramePair.dfy'
TARGET1 = 'RepoDiscoU16Frame.ReadU16Frame'
TARGET2 = 'RepoDiscoFramePair.ReadFramePair'
BEGIN, END = b'    // BEGIN REPLACEMENT\n', b'    // END REPLACEMENT\n'
FIRST = ['baseline', 'stage1-reference', 'stage2-reference']
NEGATIVE1 = ['stage1-always-failure', 'stage1-wrong-suffix', 'stage1-wrong-payload']
NEGATIVE2 = ['stage2-always-failure', 'stage2-swapped-fields', 'stage2-wrong-suffix', 'stage2-missing-second-frame']


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encode(obj):
    return (json.dumps(obj, indent=2, sort_keys=True) + '\n').encode()


def read(path):
    path = Path(path)
    assert path.is_file() and not path.is_symlink(), str(path)
    return path.read_bytes()


def split_template(raw):
    assert raw.count(BEGIN) == raw.count(END) == 1
    before, remaining = raw.split(BEGIN)
    body, after = remaining.split(END)
    assert body == b''
    return before + BEGIN, END + after


def original_stage1_parts(raw):
    declaration = b'  function method {:opaque} ReadU16Frame('
    assert raw.count(declaration) == 1
    start = raw.index(b'\n  {\n', raw.index(declaration)) + len(b'\n  {\n')
    suffix = b'  }\n}\n\n'
    assert raw.endswith(suffix)
    return raw[:start], raw[start:-len(suffix)], suffix


def closure(roots, sources):
    pending, found = list(roots), set()
    while pending:
        name = pending.pop()
        if name in found:
            continue
        assert name in sources, name
        found.add(name)
        for included in re.findall(r'^\s*include\s+"([^"\r\n]+)"', sources[name].decode(), re.M):
            parts = list(PurePosixPath(name).parent.parts)
            for part in PurePosixPath(included).parts:
                if part == '..':
                    assert parts
                    parts.pop()
                elif part != '.':
                    parts.append(part)
            pending.append('/'.join(parts))
    return found


def ancestry_pins():
    paths = [PACKAGE / 'qualification-004/transfer-aws.json',
             PACKAGE / 'qualification-004/configs/aws.json',
             PACKAGE / 'qualification-004/retrieved-aws/accounting.txt',
             PACKAGE / 'qualification-004/retrieved-aws/qualification-63088520.err',
             PACKAGE / 'qualification-004/retrieved-aws/qualification-004/output-aws/summary.json',
             PACKAGE / 'qualification-004/retrieved-aws/qualification-004/output-aws/aws-baseline-001/record.json']
    raw = PACKAGE / 'qualification-004/retrieved-aws/qualification-004/output-aws/aws-baseline-001/raw'
    paths.extend(p for p in raw.rglob('*') if p.is_file())
    return {p.relative_to(PACKAGE).as_posix():sha(read(p)) for p in sorted(paths)}


def material():
    baseline_case = json.loads(read(AWS / 'cases-001/aws-baseline-001/case.json'))
    old_sources = {item['path']:item for item in baseline_case['source_files']}
    assert len(old_sources) == 102 and set(BASE) <= set(old_sources)
    upstream = {}
    for name in BASE:
        raw = read(AWS / baseline_case['workspace'] / name)
        pin = old_sources[name]
        assert sha(raw) == pin['sha256'] and len(raw) == pin['bytes']
        assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == pin['git_blob_sha']
        upstream[name] = raw
    assert closure(BASE, upstream) == set(BASE)
    template1 = read(PACKAGE / 'pilot/draft-001/templates/aws-stage1.dfy')
    template2 = read(ROOT / 'templates/RepoDiscoFramePair.dfy')
    before1, after1 = split_template(template1)
    before2, after2 = split_template(template2)
    ref_path = AWS / 'draft/overlay' / STAGE1
    ref = read(ref_path)
    prefix, body, suffix = original_stage1_parts(ref)
    # The existing common-policy template removes exactly the old three-line
    # analyst metadata prefix and inserts body markers; declarations are exact.
    metadata = b''.join(ref.splitlines(keepends=True)[:3])
    assert all(line.startswith(b'//') for line in metadata.splitlines())
    assert before1 == prefix[len(metadata):] + BEGIN and after1 == END + suffix
    bodies = {'stage1-reference':body}
    for name in NEGATIVE1:
        negative = read(AWS / 'draft/negatives' / (name + '.dfy'))
        nprefix, nbody, nsuffix = original_stage1_parts(negative)
        assert nprefix == prefix and nsuffix == suffix
        bodies[name] = nbody
    for name in ['stage2-reference'] + NEGATIVE2:
        bodies[name] = read(ROOT / 'bodies' / (name + '.txt'))
    assert all(value.endswith(b'\n') and BEGIN not in value and END not in value for value in bodies.values())
    files = {'templates/RepoDiscoU16Frame.dfy':template1}
    files.update({'bodies/' + name + '.txt':raw for name, raw in bodies.items()})
    files['templates/RepoDiscoFramePair.dfy'] = template2
    config = json.loads(read(PACKAGE / 'qualification-004/configs/aws.json'))
    assert config['source_pin'] == 'dab800a2a610253659d113ee6e4bf8a70b86d13a'
    options = config['options']
    assert options[options.index('--cores') + 1] == '1'
    assert options[options.index('--resource-limit') + 1] == '500000000'
    assert options[options.index('--verification-time-limit') + 1] == '300'
    assert config['wall_seconds'] == 900 and '--enforce-determinism' in options
    prefix_argv = [config['dafny'], 'verify'] + options
    specs = [('baseline', 0, None, None, 'PROOF_PASS'),
             ('stage1-reference', 1, 'stage1-reference', None, 'PROOF_PASS'),
             ('stage2-reference', 2, 'stage1-reference', 'stage2-reference', 'PROOF_PASS')]
    specs += [(name, 1, name, None, 'PROOF_FAILURE') for name in NEGATIVE1]
    specs += [(name, 2, 'stage1-reference', name, 'PROOF_FAILURE') for name in NEGATIVE2]
    specs += [('unproved-parent-reference-child', 2, 'stage1-always-failure', 'stage2-reference', 'PROOF_FAILURE'),
              ('stage2-omitted-from-roots', 2, 'stage1-reference', 'stage2-always-failure', 'COVERAGE_OMISSION')]
    cases = []
    for ident, stage, parent, child, expected in specs:
        sources = dict(upstream)
        if parent is not None:
            sources[STAGE1] = before1 + bodies[parent] + after1
        if child is not None:
            sources[STAGE2] = before2 + bodies[child] + after2
        scope = BASE + ([STAGE1] if stage >= 1 else []) + ([STAGE2] if stage == 2 else [])
        omitted = [STAGE2] if expected == 'COVERAGE_OMISSION' else []
        command_files = [name for name in scope if name not in omitted]
        assert closure(command_files, sources) == set(sources) - set(omitted)
        bad_parent = stage == 1 or ident == 'unproved-parent-reference-child'
        failed = [TARGET1 if bad_parent else TARGET2] if expected == 'PROOF_FAILURE' else []
        passed = ([TARGET1] if stage >= 1 and not failed == [TARGET1] else [])
        if stage == 2 and expected == 'PROOF_PASS':
            passed.append(TARGET2)
        workspace = 'cases/' + ident + '/workspace'
        files.update({workspace + '/' + name:raw for name, raw in sources.items()})
        cases.append(dict(id=ident, workspace_dir=workspace, stage=stage,
            stage_id='baseline' if stage == 0 else 'u16-frame' if stage == 1 else 'frame-pair',
            source_sha256={name:sha(raw) for name,raw in sorted(sources.items())},
            command_files=command_files, declared_scope_files=scope, argv=prefix_argv + command_files,
            expected_category=expected, expected_native_category='PROOF_PASS' if expected == 'COVERAGE_OMISSION' else expected,
            expected_failed_targets=failed, expected_passed_targets=passed,
            required_targets=([TARGET1] if stage >= 1 else []) + ([TARGET2] if stage == 2 else []),
            omitted_targets=[TARGET2] if omitted else [], omit_from_command=omitted,
            omitted_source_all_units=omitted,
            inspect_targets=[TARGET2] if ident == 'unproved-parent-reference-child' else [],
            child_outcome_predetermined=False if ident == 'unproved-parent-reference-child' else None,
            parent_body=parent, child_body=child,
            source_revision='aws/revision-002', native_status='UNKNOWN', actual_native_unit_labels=None,
            classification_requires_named_units_and_exact_inventory=True,
            gated_until_positive_review=ident not in FIRST,
            native_dispatch_authorized=False, analyst_authored=True, model_acceptance=False))
    files['cases.json'] = encode(cases)
    inputs = {'aws/cases-001/aws-baseline-001/case.json':sha(read(AWS / 'cases-001/aws-baseline-001/case.json')),
              'aws/draft/overlay/' + STAGE1:sha(ref),
              'pilot/draft-001/templates/aws-stage1.dfy':sha(template1),
              'qualification-004/configs/aws.json':sha(read(PACKAGE / 'qualification-004/configs/aws.json'))}
    for name in NEGATIVE1:
        path = 'aws/draft/negatives/' + name + '.dfy'
        inputs[path] = sha(read(PACKAGE / path))
    files['revision.json'] = encode(dict(
        schema='repodisco-aws-uint-component-revision-v1', status='PREPARED_NATIVE_UNKNOWN',
        source_pin=config['source_pin'], verifier_version=config['expected_version'],
        rationale='The prior 102-source AWS component failed qualification. This is a newly declared narrow UInt component and raw-frame-pair task, not a repaired or rescored broad component.',
        failed_ancestor=dict(job_id='63088520', scope_source_count=102,
            observations=['legacy nonlinear-arithmetic call precondition failures',
                          'array initialization rejected by enforce-determinism',
                          '900-second outer timeout', 'Slurm 4GB out-of-memory termination'],
            evidence_sha256=ancestry_pins(), unchanged=True),
        current_scope=dict(explicit_baseline_roots=BASE, source_sha256={name:sha(raw) for name,raw in upstream.items()},
            include_closure=sorted(closure(BASE, upstream)), complete_repository_claim=False,
            not_in_this_new_component=sorted(set(old_sources) - set(BASE))),
        stage1=dict(path=STAGE1, target=TARGET1, stage_id='u16-frame', unchanged_contract_and_body=True,
            template_origin='pilot/draft-001/templates/aws-stage1.dfy',
            marker_lines=[BEGIN.decode().rstrip('\n'),END.decode().rstrip('\n')],
            old_reference_transform='Existing template omits only the exact three leading analyst metadata lines and inserts the two host body markers. The original body and every declaration/specification/import byte remain unchanged.'),
        stage2=dict(path=STAGE2, target=TARGET2, stage_id='frame-pair', meaning='Two consecutive uint16-length-prefixed raw-byte fields plus remaining suffix',
            excludes=['UTF8 validity','encryption-context maps','canonical context format','complete MPL repository'],
            parent_call_count=2, required_reuse=False,
            contract=['success iff two complete frames','exact left/right/suffix','both uint16 length bounds','whole input re-encoding identity']),
        native_policy=dict(command_prefix=prefix_argv, outer_wall_seconds=900,
                           verification_time_limit_seconds=300, resource_limit=500000000,
                           cpus=1,memory_gib=4,resources_changed=False,no_automatic_retry=True),
        first_native_phase=FIRST,
        gated_controls=[case['id'] for case in cases if case['id'] not in FIRST],
        gate='All three new positive cases and complete source-bound native inventories must pass review before any of nine distinct controls. Earlier broad-scope evidence is never promoted into these new positives.',
        inherited_input_sha256=inputs, model_execution_authorized=False,native_calls=0,model_calls=0,
    ))
    files['manifest.json'] = encode(dict(schema='repodisco-aws-uint-revision-manifest-v1',
        files={name:sha(raw) for name,raw in sorted(files.items())},positive_cases=3,gated_controls=9,
        native_status='UNKNOWN',model_calls=0))
    return files


def build():
    files=material()
    for name,raw in files.items():
        path=ROOT/name
        if path.exists():
            assert path.is_file() and path.read_bytes()==raw,name
        else:
            path.parent.mkdir(parents=True,exist_ok=True)
            with path.open('xb') as stream:stream.write(raw)
    return dict(positive_cases=3,gated_controls=9,source_files=sum(name.startswith('cases/') and name.endswith('.dfy') for name in files),
                cases_sha256=sha(files['cases.json']),manifest_sha256=sha(files['manifest.json']),native_calls=0,model_calls=0)


if __name__=='__main__':
    print(json.dumps(build(),indent=2,sort_keys=True))
