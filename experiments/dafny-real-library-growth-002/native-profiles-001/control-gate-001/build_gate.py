"""Assemble the concrete 30-expectation gate from retained native evidence.

No verifier/provider/SSH/job/Git operation exists here. All source-bound saved
reviews must replay before any profile, replay receipt or passing gate is written.
"""
from collections import Counter
from contextlib import contextmanager
import copy
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
EXPERIMENT = HERE.parents[1]
sys.path.insert(0, str(EXPERIMENT / 'common'))
import review_native as native
import guard

REFERENCE_GATE = 'native-profiles-001/reference-gate.json'
REFERENCE_SHA = '18888e38c1437b451595ff928a2c1ce1cd5908d405263ec54b46427e431d0b27'
AUDIT = 'native-profiles-001/reviews/controls-audit-001/audit.json'
AUDIT_SHA = 'b5389fae411ca4c9bc0a76f98a3c26db188965cbf72de4e33a0e00b1d741f0fa'
RETIRED = {'splice-no-tail-pop', 'splice-unproved-seed'}
REPLACEMENTS = {'splice-retains-old-content', 'splice-unproved-seed-rebuild'}
COUNTS = {'stdlib-filter': 7, 'stdlib-splice': 7, 'aws-batch': 6, 'aws-tagged': 6}
PINS = {}
OUTPUTS = {}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def read(relative, task_pins=None):
    require(native.safe_path(relative), 'Unsafe experiment-relative path')
    path = EXPERIMENT / relative
    require(path.is_file() and not path.is_symlink(), 'Missing/linked evidence: ' + relative)
    raw = path.read_bytes()
    digest = native.sha(raw)
    PINS[relative] = digest
    if task_pins is not None:
        task_pins[relative] = digest
    return raw


def obj(relative, task_pins=None):
    return json.loads(read(relative, task_pins))


def pretty(value):
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()


def defer(relative, value, task_pins=None):
    full = HERE.relative_to(EXPERIMENT).as_posix() + '/' + relative
    require(native.safe_path(full) and full not in OUTPUTS and not (EXPERIMENT / full).exists(),
            'Exclusive output already exists: ' + full)
    raw = pretty(value)
    OUTPUTS[full] = raw
    PINS[full] = native.sha(raw)
    if task_pins is not None:
        task_pins[full] = PINS[full]
    return dict(path=full, sha256=PINS[full])


@contextmanager
def reviewer(runtime):
    names = ('native_scorer', 'collect', 'ops', '_final_control_review')
    old = {name: sys.modules.get(name) for name in names}
    try:
        for name, file in zip(names, ('native_scorer.py', 'collect.py', 'ops.py', 'review.py')):
            relative = runtime + '/' + file
            read(relative)
            spec = importlib.util.spec_from_file_location(name, EXPERIMENT / relative)
            module = importlib.util.module_from_spec(spec)
            sys.modules[name] = module
            spec.loader.exec_module(module)
        yield sys.modules[names[-1]]
    finally:
        for name, previous in old.items():
            if previous is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous


def observe(folder, task_pins=None):
    record = obj(folder + '/record.json', task_pins)
    source_pins = {name: dict(path=folder + '/workspace/' + name, sha256=digest)
                   for name, digest in record['source_before_sha256'].items()}
    raw_pins = {name: dict(path=folder + '/raw/' + name, sha256=digest)
               for name, digest in record['raw_sha256'].items()}
    sources = {name: read(pin['path'], task_pins) for name, pin in source_pins.items()}
    raw = {name: read(pin['path'], task_pins) for name, pin in raw_pins.items()}
    require(native.hashes(sources) == record['source_before_sha256'] == record['source_after_sha256'], 'Source identity drift')
    require(native.hashes(raw) == record['raw_sha256'], 'Raw identity drift')
    require(record['origin'] == 'analyst_qualification' and record['attempts'] == 1 and record['model_calls'] == 0,
            'Unexpected analyst observation provenance')
    return record, sources, raw, source_pins, raw_pins


def inspect_run(runtime, project, expected_matches):
    saved_path = runtime + '/reviews/native-' + project + '-001.json'
    saved = obj(saved_path)
    with reviewer(runtime) as module:
        replayed = module.review(project)
    require(native.canonical(saved) == native.canonical(replayed), 'Saved qualification review no longer replays')
    require(not saved['missing_records'] and saved['model_calls'] == 0, 'Missing control observations')
    require(sum(row['expectation']['expected_match'] for row in saved['observations']) == expected_matches,
            'Unexpected matching control count')
    receipt = obj(runtime + '/transfer-' + project + '.json')
    archive = runtime + '/retrieved-' + project
    for name, entry in receipt['files'].items():
        raw = read(archive + '/' + name)
        require(len(raw) == entry['bytes'] and native.sha(raw) == entry['sha256'], 'Archive member drift')
    compressed = read(runtime + '/transfer-' + project + '.tar.gz')
    require(native.sha(compressed) == receipt['archive_sha256'] and len(compressed) == receipt['compressed_bytes'],
            'Compressed archive drift')
    for suffix in ('reference-gate-binding.json', 'tool-profiles.json', 'configs/' + project + '.json',
                   'control-metadata/' + project + '.json', 'freezes/' + project + '.json',
                   'submissions/' + project + '.json'):
        read(runtime + '/' + suffix)
    config = obj(runtime + '/configs/' + project + '.json')
    metadata = obj(runtime + '/control-metadata/' + project + '.json')
    catalog = obj(metadata['source_path'])
    require(native.sha(read(metadata['source_path'])) == metadata['source_sha256'], 'Control catalog drift')
    originals = {case['id']: case for case in catalog}
    controls = {case['id']: case for case in metadata['cases']}
    require(all(originals[cid] == case for cid, case in controls.items()), 'Frozen expectation metadata changed')
    fixture_root = Path(metadata['source_path']).parent
    manifest = obj((fixture_root / 'manifest.json').as_posix())
    cases = {case['id']: case for case in config['cases']}
    rows = []
    for row in saved['observations']:
        cid = row['case_id']
        case = cases[cid]
        folder = archive + '/' + runtime + '/output-' + project + '/' + cid
        record, sources, raw, source_pins, raw_pins = observe(folder)
        require(native.hashes(sources) == case['source_sha256'] == controls[cid]['source_sha256'], 'Control source/config drift')
        for name, value in sources.items():
            path = (Path(case['workspace_dir']) / name)
            require(read(path.as_posix()) == value and manifest['files'][path.relative_to(fixture_root).as_posix()] == native.sha(value),
                    'Control source differs from exact frozen fixture')
        require(record['argv'] == [config['dafny'], 'verify'] + config['options'] + case['command_files'],
                'Exact control native command changed')
        require(record['toolchain'] == record['toolchain_after'] and record['host']['cpus_per_task'] == 1,
                'Tool/resource provenance drift')
        rows.append(dict(runtime=runtime, project=project, folder=folder, case=case, metadata=controls[cid],
            saved=row, record=record, sources=sources, raw=raw, source_pins=source_pins, raw_pins=raw_pins))
    return rows


def same_except_profile(before, after):
    before, after = copy.deepcopy(before), copy.deepcopy(after)
    before.pop('profile_sha256');after.pop('profile_sha256')
    require(native.canonical(before) == native.canonical(after), 'Extending exclusion lists altered native outcome or coverage')


def main():
    # Fail before constructing any output until real replacement evidence exists.
    replacement_review = obj('qualification-007/reviews/native-stdlib-001.json')
    require(replacement_review['all_expected_match'] is True
            and {row['case_id'] for row in replacement_review['observations']} == REPLACEMENTS
            and all(row['expectation']['expected_match'] is True for row in replacement_review['observations']),
            'Both actual replacement controls must match before gate generation')
    reference = obj(REFERENCE_GATE)
    require(native.sha(read(REFERENCE_GATE)) == REFERENCE_SHA and reference['status'] == 'PASS'
            and reference['all_references_match'] is True and reference['model_calls'] == 0,
            'Exact four-reference gate required')
    for path, digest in reference['input_files'].items():
        require(native.sha(read(path)) == digest, 'Reference gate pin drift: ' + path)
    audit = obj(AUDIT)
    require(native.sha(read(AUDIT)) == AUDIT_SHA and audit['total_expected_matches'] == 24
            and audit['total_observations'] == 26 and set(audit['unmatched_case_ids']) == RETIRED,
            'Exact independent q002 audit required')
    for path, digest in audit['input_files'].items():
        require(native.sha(read(path)) == digest, 'Independent audit input drift: ' + path)
    read(Path(__file__).relative_to(EXPERIMENT).as_posix())
    for path in ('common/review_native.py', 'common/guard.py',
                 'qualification-007/control-revision-binding.json', 'control-revision-001/manifest.json'):
        read(path)
    old_controls = inspect_run('qualification-002', 'stdlib', 12) + inspect_run('qualification-002', 'aws', 12)
    replacements = inspect_run('qualification-007', 'stdlib', 2)
    require(len(old_controls) == 26 and len(replacements) == 2, 'Wrong fixed control set')
    require({row['case']['id'] for row in old_controls if not row['saved']['expectation']['expected_match']} == RETIRED,
            'Original resource misses were relabeled or replaced in place')
    require(all(row['saved']['observation']['category'] == 'RESOURCE_FAILURE' for row in old_controls
                if row['case']['id'] in RETIRED), 'Original misses no longer retain resource classification')
    require({row['case']['id'] for row in replacements} == REPLACEMENTS
            and all(row['saved']['expectation']['expected_match'] for row in replacements), 'Replacement controls did not qualify')
    controls = [row for row in old_controls if row['case']['id'] not in RETIRED] + replacements
    require(len(controls) == 26 and Counter(row['case']['task_id'] for row in controls) == Counter(COUNTS),
            'Active control allocation differs')
    all_observed = old_controls + replacements
    new_runs = {row['record']['run_id'] for row in all_observed}
    new_raw = {native.sha(native.canonical(native.hashes(row['raw']))) for row in all_observed}
    require(len(new_runs) == 28, 'Duplicate native observation was counted twice')
    denied_runs = sorted(set(reference['ineligible_parent_runs']) | new_runs)
    denied_raw = sorted(set(reference['ineligible_parent_raw_fingerprints']) | new_raw)
    task_pins = {task: dict(entry['input_files']) for task, entry in reference['tasks'].items()}
    profiles, profile_pins, reference_receipts = {}, {}, {}
    for task_id, entry in reference['tasks'].items():
        pins = task_pins[task_id]
        original = obj(entry['native_profile']['path'], pins)
        profile = copy.deepcopy(original)
        profile['ineligible_parent_runs'] = denied_runs
        profile['ineligible_parent_raw_fingerprints'] = denied_raw
        changed = [key for key in profile if profile[key] != original[key]]
        require(set(changed) <= {'ineligible_parent_runs', 'ineligible_parent_raw_fingerprints'}, 'Proof policy unexpectedly changed')
        profiles[task_id] = profile
        profile_pins[task_id] = defer('profiles/' + task_id + '.json', profile, pins)
        profile_pins[task_id]['canonical_sha256'] = native.sha(native.canonical(profile))
        folder = str(Path(entry['reference_record']['path']).parent)
        record, sources, raw, source_map, raw_map = observe(folder, pins)
        evidence = native.EvidencePins(native.sha(native.canonical(profile)), native.sha(native.canonical(record)),
            native.sha(native.canonical(native.hashes(sources))), tuple(sorted(native.hashes(raw).items())),
            record['run_id'], 'analyst_qualification')
        replay = native.review(profile, sources, record, raw, evidence)
        original_review = obj(entry['native_review']['path'], pins)
        same_except_profile(original_review['replay'], replay)
        require(replay['qualified_success'] and replay['strict_zero_warning_success'] and replay['proof_coverage_complete'],
                'Reference no longer qualifies under versioned exclusion profile')
        receipt = dict(task_id=task_id, case_id=entry['reference_case_id'], kind='selected_reference',
            expected_match=True, expected_category='PROOF_PASS', actual_category=replay['category'],
            record=entry['reference_record'], source_files=source_map, raw_files=raw_map,
            source_fixture_binding=entry['fixture_binding'], native_review=replay,
            original_native_profile=entry['native_profile'], extended_native_profile=profile_pins[task_id],
            policy_fields_changed=changed, new_native_observations=0, model_calls=0, model_acceptance=False)
        reference_receipts[task_id] = defer('replays/references/' + task_id + '.json', receipt, pins)
    active_controls = {task: [] for task in COUNTS}
    for row in controls:
        task_id, cid = row['case']['task_id'], row['case']['id']
        pins = task_pins[task_id]
        record, sources, raw, source_map, raw_map = observe(row['folder'], pins)
        profile = profiles[task_id]
        require(record['run_id'] in profile['ineligible_parent_runs']
                and native.sha(native.canonical(native.hashes(raw))) in profile['ineligible_parent_raw_fingerprints'],
                'Fresh analyst control absent from live-profile exclusions')
        with reviewer(row['runtime']) as module:
            current = module.review_case(row['case'], row['metadata'], EXPERIMENT / row['folder'],
                                         profile, profile_pins[task_id], record['host']['job_id'])
        require(current['expectation']['expected_match'] is True, 'Control does not match with extended exclusion profile')
        same_except_profile(row['saved']['observation'], current['observation'])
        require(native.canonical(row['saved']['expectation']) == native.canonical(current['expectation']),
                'Frozen expected outcome changed')
        require(current['observation']['warnings'] == 0 and not current['observation']['extra_units'], 'New warnings/extra obligations')
        if cid in REPLACEMENTS:
            require(current['observation']['category'] == 'PROOF_FAILURE'
                    and current['observation']['proof_coverage_complete'], 'Replacement is not complete ordinary proof failure')
            require(current['expectation']['passed_targets_match'] and current['expectation']['failed_targets_match'],
                    'Replacement named parent/caller outcomes differ')
            edit = obj(reference['tasks'][task_id]['edit_profile']['path'], pins)
            prefix, suffix = guard._profile(edit)
            addition = sources[edit['addition']['path']]
            require(addition.startswith(prefix.encode()) and addition.endswith(suffix.encode()), 'Replacement changed target contract')
        receipt = dict(task_id=task_id, case_id=cid, kind='control', runtime=row['runtime'],
            record=dict(path=row['folder'] + '/record.json', sha256=native.sha(read(row['folder'] + '/record.json', pins))),
            source_files=source_map, raw_files=raw_map, expected_match=True,
            expectation=current['expectation'], native_review=current['observation'],
            materialized_profile_sha256=native.sha(native.canonical(current['materialized_profile'])),
            materialization_code=dict(path=row['runtime'] + '/review.py', sha256=PINS[row['runtime'] + '/review.py']),
            source_case_metadata=row['metadata'], unlogged_source_bindings=current['unlogged_source_bindings'],
            new_native_observations=0, model_calls=0, model_acceptance=False)
        replay_pin = defer('replays/controls/' + row['runtime'] + '-' + cid + '.json', receipt, pins)
        active_controls[task_id].append(dict(case_id=cid, runtime=row['runtime'], run_id=record['run_id'],
            expected_category=current['expectation']['expected_category'], actual_category=current['observation']['category'],
            expected_match=True, replay=replay_pin))
    tasks = {}
    for task_id, entry in reference['tasks'].items():
        pins = task_pins[task_id]
        for pin in [entry['edit_profile'], *entry['base_sources'].values()]:
            read(pin['path'], pins)
        tasks[task_id] = dict(qualified_success=True, all_controls_match=True,
            reference_case_id=entry['reference_case_id'], reference_review=reference_receipts[task_id],
            native_profile=profile_pins[task_id], original_native_profile=entry['native_profile'],
            edit_profile=entry['edit_profile'], base_sources=entry['base_sources'],
            control_count=len(active_controls[task_id]), active_controls=active_controls[task_id],
            named_units=entry['named_units'], inherited_unit_count=entry['inherited_unit_count'],
            fixture_binding=entry['fixture_binding'], input_files=dict(sorted(pins.items())))
    retained = [dict(case_id=row['case']['id'], runtime=row['runtime'], run_id=row['record']['run_id'],
        expected_category=row['metadata']['expected_category'], actual_category=row['saved']['observation']['category'],
        expected_match=False, counted_in_active_matrix=False, original_expectation_preserved=True,
        record=dict(path=row['folder'] + '/record.json', sha256=PINS[row['folder'] + '/record.json']),
        raw_files=row['raw_pins'], source_files=row['source_pins'])
        for row in old_controls if row['case']['id'] in RETIRED]
    complex_path = 'qualification-005/retrieved-stdlib/qualification-005/output-stdlib/splice-reference'
    complex_record, _, complex_raw, complex_sources, complex_raw_pins = observe(complex_path)
    require(complex_record['exit_code'] != 0 and b'out of resource' in complex_raw['stdout.txt'].lower(),
            'Retired complex reference failure is no longer preserved')
    retained.append(dict(case_id='splice-reference', runtime='qualification-005', run_id=complex_record['run_id'],
        expected_category='PROOF_PASS', actual_category='RESOURCE_FAILURE', expected_match=False,
        counted_in_active_matrix=False, original_expectation_preserved=True,
        record=dict(path=complex_path + '/record.json', sha256=PINS[complex_path + '/record.json']),
        raw_files=complex_raw_pins, source_files=complex_sources))
    category_counts = Counter(item['actual_category'] for values in active_controls.values() for item in values)
    require(category_counts == Counter({'VERIFIED':1, 'PROOF_FAILURE':21, 'COVERAGE_FAILURE':4}), 'Active control categories differ')
    profile_extension = defer('profile-extension-review.json', dict(
        purpose='Extend the existing runner-enforced analyst provenance exclusions; native proof policy and source scope unchanged.',
        original_reference_gate=dict(path=REFERENCE_GATE, sha256=REFERENCE_SHA),
        changed_fields=['ineligible_parent_runs','ineligible_parent_raw_fingerprints'],
        newly_bound_native_runs=sorted(new_runs), excluded_native_run_count=len(denied_runs),
        excluded_raw_fingerprint_count=len(denied_raw), native_profiles=profile_pins,
        original_profiles_unchanged=True, new_native_calls=0, model_calls=0))
    result = dict(schema='repodisco-varied-growth-control-gate-v1', status='PASS', all_expected_match=True,
        model_calls=0, new_native_calls=0, native_observations_replayed=32,
        active_expectation_count=30, selected_reference_count=4, active_control_count=26,
        reused_matching_q002_controls=24, distinct_q007_replacement_controls=2,
        active_control_category_counts=dict(category_counts), tasks=tasks,
        reference_gate=dict(path=REFERENCE_GATE, sha256=REFERENCE_SHA),
        independent_q002_audit=dict(path=AUDIT, sha256=AUDIT_SHA),
        profile_extension_review=profile_extension,
        ineligible_parent_runs=denied_runs, ineligible_parent_raw_fingerprints=denied_raw,
        retained_outside_active_matrix=retained,
        historical_reference_exclusions=reference['excluded_analyst_observations'],
        input_files=dict(sorted(PINS.items())), execution_authorized=False,
        interpretation='Expected failures and omissions qualify test sensitivity; they are not proof passes or model successes. Reuse does not create new independent native trials.',
        manual_root_review='pending', original_expectations_and_archives_unchanged=True)
    # Only after every replay and named expectation has succeeded, emit outputs.
    gate_path = HERE / 'gate.json'
    require(not gate_path.exists(), 'A control gate already exists; no overwrite/restart')
    for path in OUTPUTS:
        require(not (EXPERIMENT / path).exists(), 'Output appeared during review')
    for path, raw in OUTPUTS.items():
        target = EXPERIMENT / path
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            stream.write(raw)
    with gate_path.open('xb') as stream:
        stream.write(pretty(result))
    print(json.dumps(dict(status='PASS', active_expectations=30, controls=26,
        category_counts=dict(category_counts), profile_excluded_runs=len(denied_runs),
        gate_sha256=native.sha(gate_path.read_bytes()), input_files=len(PINS), model_calls=0, new_native_calls=0)))


if __name__ == '__main__':
    main()
