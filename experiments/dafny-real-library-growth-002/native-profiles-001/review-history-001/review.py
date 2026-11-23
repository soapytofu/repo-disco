"""Offline source-bound native profile mapping and four-reference release gate.

Inspection can retain partial success; only build with all four actual passing
references may write reference-gate.json. No native/network/provider operations.
"""
import argparse
from collections import Counter
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
EXPERIMENT = HERE.parent
sys.path.insert(0, str(EXPERIMENT / 'common'))
import guard
import review_native as native
import mapping

TASK_IDS = ('stdlib-filter', 'stdlib-splice', 'aws-batch', 'aws-tagged')
INHERITED_COUNTS = {'stdlib-filter': 56, 'stdlib-splice': 58, 'aws-batch': 77, 'aws-tagged': 77}


def checked(relative):
    native.require(native.safe_path(relative), 'Unsafe experiment-relative input path')
    path = EXPERIMENT / relative
    native.require(path.is_file() and not any(p.is_symlink() for p in (path, *path.parents)
                   if p != EXPERIMENT.parent), 'Missing/symlink evidence input: ' + relative)
    return path


def read(relative, pins):
    path = checked(relative)
    raw = path.read_bytes()
    pins[relative] = native.sha(raw)
    return raw


def obj(relative, pins):
    return json.loads(read(relative, pins))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def load_observation(relative, pins):
    folder = EXPERIMENT / relative
    record = obj(relative + '/record.json', pins)
    sources = {p.relative_to(folder / 'workspace').as_posix():
               read(p.relative_to(EXPERIMENT).as_posix(), pins)
               for p in sorted((folder / 'workspace').rglob('*.dfy'))}
    raw = {p.relative_to(folder / 'raw').as_posix(): read(p.relative_to(EXPERIMENT).as_posix(), pins)
           for p in sorted((folder / 'raw').rglob('*')) if p.is_file()}
    native.require(sources and raw, 'Missing exact source/raw evidence')
    native.require(record['source_before_sha256'] == native.hashes(sources) == record['source_after_sha256'],
                   'Observed source hashes changed')
    native.require(record['raw_sha256'] == native.hashes(raw), 'Observed raw hashes changed')
    native.require(record['toolchain'] == record['toolchain_after'], 'Observed tool bytes changed')
    native.require(record['origin'] == 'analyst_qualification' and record['attempts'] == 1
                   and record['model_calls'] == 0, 'Reference provenance differs')
    return record, sources, raw


def preliminary(runtime_root, project, pins):
    """Invoke only the existing read-only archive reviewer, with scoped imports."""
    names = ('native_scorer', 'collect', 'ops', '_growth_reference_archive_review')
    prior = {name: sys.modules.get(name) for name in names}
    try:
        for name, filename in zip(names, ('native_scorer.py', 'collect.py', 'ops.py', 'review.py')):
            path = checked(runtime_root + '/' + filename)
            read(path.relative_to(EXPERIMENT).as_posix(), pins)
            spec = importlib.util.spec_from_file_location(name, path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[name] = module
            spec.loader.exec_module(module)
        reviewer = sys.modules[names[-1]]
        result = reviewer.review(project)
        config = obj(runtime_root + '/configs/' + project + '.json', pins)
        receipt = obj(runtime_root + '/transfer-' + project + '.json', pins)
        obj(runtime_root + '/submissions/' + project + '.json', pins)
        obj(runtime_root + '/freezes/' + project + '.json', pins)
        obj(runtime_root + '/tool-profiles.json', pins)
        obj(runtime_root + '/reference-metadata/' + project + '.json', pins)
        archive = runtime_root + '/retrieved-' + project
        read(archive + '/accounting.txt', pins)
        obj(archive + '/submission.json', pins)
        # All archive members were checked against the transfer receipt by the
        # existing reviewer. The selected raw/source evidence is pinned below.
        native.require(result['job_id'] == receipt['job_id'], 'Reviewed archive job differs')
        return result, config
    finally:
        for name, value in prior.items():
            if value is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = value


def exclusions(selection, selected, pins):
    runs, fingerprints, observations = set(), set(), []
    inherited_paths = sorted(set(binding['inherited_profile'] for binding in selected.values()))
    # Retain both families' already-reviewed exclusion lists even in an AWS-only
    # inspection; future selected observations are added when actually present.
    inherited_paths = sorted(set(inherited_paths) | set(selection['inherited_exclusion_profiles']))
    for path in inherited_paths:
        profile = obj(path, pins)
        runs.update(profile['ineligible_parent_runs'])
        fingerprints.update(profile['ineligible_parent_raw_fingerprints'])
    paths = sorted(set(selection.get('excluded_observations', [])) |
                   {binding['observation'] for binding in selected.values()})
    for path in paths:
        record, _, raw = load_observation(path, pins)
        fingerprint = native.sha(native.canonical(native.hashes(raw)))
        runs.add(record['run_id'])
        fingerprints.add(fingerprint)
        observations.append(dict(path=path, run_id=record['run_id'], exit_code=record['exit_code'],
            raw_fingerprint_sha256=fingerprint, eligible_model_parent=False,
            role='selected reference' if path in {b['observation'] for b in selected.values()} else 'excluded prior observation'))
    return sorted(runs), sorted(fingerprints), observations


def inspect_task(task_id, binding, denied_runs, denied_raw, cache, pins):
    native.require(task_id in TASK_IDS and binding['family'] in {'stdlib', 'aws'}, 'Unknown task binding')
    family = binding['family']
    key = (binding['runtime_root'], family)
    if key not in cache:
        cache[key] = preliminary(*key, pins)
    preliminary_result, config = cache[key]
    for relative in (binding['runtime_root'] + '/configs/' + family + '.json',
                     binding['runtime_root'] + '/freezes/' + family + '.json',
                     binding['runtime_root'] + '/transfer-' + family + '.json',
                     binding['runtime_root'] + '/submissions/' + family + '.json'):
        read(relative, pins)
    matches = [c for c in config['cases'] if c['id'] == binding['case_id']]
    native.require(len(matches) == 1 and matches[0]['task_id'] == task_id, 'Native config task identity differs')
    case = matches[0]
    expected_path = binding['runtime_root'] + '/retrieved-' + family + '/' + binding['runtime_root'] + '/output-' + family + '/' + case['id']
    native.require(binding['observation'] == expected_path, 'Observation is outside its exact declared output')
    initial = [r for r in preliminary_result['observations'] if r['case_id'] == case['id']]
    native.require(len(initial) == 1 and initial[0]['category'] == 'NATIVE_SUCCESS_INVENTORY_PENDING'
                   and initial[0]['warning_count'] == 0 and not initial[0]['missing_inherited_units']
                   and not initial[0]['nonpassing_inherited_units'], 'Reference did not pass preliminary native checks')
    record, sources, raw = load_observation(binding['observation'], pins)
    native.require(record['exit_code'] == 0 and not record['timeout'], 'Reference is not a complete zero-exit success')
    edit = obj(binding['edit_profile'], pins)
    native.require(edit['project'] == task_id and edit['stage'] == 1 and edit['parent_requirement'] is None,
                   'Task must be an independent stage-one protected addition')
    guard._profile(edit)
    base = {name: read(path, pins) for name, path in binding['base_sources'].items()}
    native.require(native.hashes(base) == edit['base_source_sha256'], 'Fixed base differs from edit profile')
    native.require(all(sources.get(name) == data for name, data in base.items()), 'Reference changed the immutable base')
    prefix, suffix = guard._profile(edit)
    added = sources[edit['addition']['path']]
    native.require(added.startswith(prefix.encode()) and added.endswith(suffix.encode()), 'Reference changed fixed headers')
    body = added[len(prefix.encode()):len(added) - len(suffix.encode())].decode()
    rebuilt, edit_audit = guard.reconstruct(edit, body, base, 'analyst-reference:' + task_id)
    native.require(rebuilt == sources, 'Reference is not exact protected-body reconstruction')
    native.require(native.hashes(sources) == case['source_sha256'], 'Reference differs from frozen native case')
    native.require(case['command_files'] == edit['verification_inputs'], 'Native and edit scope order differs')
    for name in sources:
        source_path = case['workspace_dir'] + '/' + name
        native.require(read(source_path, pins) == sources[name], 'Native source differs from selected fixture')
    fixture = obj(binding['fixture_manifest'], pins)
    native.require(isinstance(fixture.get('files'), dict), 'Fixture manifest missing exact pins')
    inherited = obj(binding['inherited_profile'], pins)
    native.require(len(inherited['required_units']) == INHERITED_COUNTS[task_id], 'Wrong inherited unit count')
    native.require(record['toolchain'] == inherited['toolchain'], 'Inherited pinned toolchain differs')
    rows, definitions, unlogged, multiplicities = mapping.inventory(family, sources, raw, inherited)
    units = {row['label']: row['file'] for row in rows}
    inherited_actual = {label: file for label, file in units.items() if file in base}
    native.require(inherited_actual == inherited['required_units'], 'Inherited native inventory or ownership changed')
    target_units = sorted(label for label in units if label.startswith(binding['target'] + ' ('))
    native.require(target_units and all(units[label] == edit['addition']['path'] for label in target_units),
                   'Primary task target has no actual native obligation')
    if edit['addition']['kind'] in {'method', 'lemma'}:
        native.require(any(label.startswith(binding['target'] + ' (correctness)') for label in target_units),
                       'Executable method target lacks actual correctness obligation')
    profile = dict(schema=native.PROFILE_SCHEMA, project=task_id, stage=1, stage_id=edit['stage_id'],
        inventory_status='qualified', command=record['argv'], verification_inputs=case['command_files'],
        toolchain=record['toolchain'], csv_columns=inherited['csv_columns'], random_seed=inherited['random_seed'],
        required_units=dict(sorted(units.items())), unitless_files={}, unlogged_definitions=unlogged,
        inherited_warnings=[], ineligible_parent_runs=denied_runs,
        ineligible_parent_raw_fingerprints=denied_raw,
        actual_target_units=target_units, source_observation=dict(path=binding['observation'], run_id=record['run_id'],
            record_file_sha256=pins[binding['observation'] + '/record.json'],
            source_revision_sha256=native.sha(native.canonical(native.hashes(sources)))),
        scope_origin='Actual analyst reference over exact frozen base bytes; not a newly accepted model revision.',
        execution_release_issued=False, negative_controls_release='pending separate review')
    evidence = native.EvidencePins(native.sha(native.canonical(profile)), native.sha(native.canonical(record)),
        native.sha(native.canonical(native.hashes(sources))), tuple(sorted(native.hashes(raw).items())),
        record['run_id'], record['origin'])
    replay = native.review(profile, sources, record, raw, evidence)
    native.require(replay['qualified_success'] and replay['strict_zero_warning_success']
                   and replay['proof_coverage_complete'] and replay['resources']['complete']
                   and replay['resources']['exit_status'] == 0 and not replay['synthetic'],
                   'Strict complete native replay did not qualify')
    report = dict(task_id=task_id, reference_case_id=case['id'], qualified_success=True,
        inherited_unit_count=INHERITED_COUNTS[task_id], inherited_inventory_unchanged=True,
        actual_target_units=target_units, named_units=len(rows), unlogged_definition_count=len(unlogged),
        unlogged_definitions_are_not_passes=True, source_sha256=native.hashes(sources),
        exact_guarded_reconstruction=True, edit_audit=edit_audit, replay=replay,
        new_units=sorted(set(units) - set(inherited['required_units'])), model_calls=0)
    mapped = dict(definitions=definitions, units=rows, native_unit_multiplicities=multiplicities,
        source_sha256=native.hashes(sources), unlogged_definitions=unlogged,
        unlogged_definitions_are_not_passes=True)
    return profile, mapped, report


def run(selection_path, task_ids=None, inspection=None):
    pins = {}
    selection_relative = Path(selection_path).resolve().relative_to(EXPERIMENT).as_posix()
    selection = obj(selection_relative, pins)
    native.require(selection['schema'] == 'dafny-growth-reference-selection-v1', 'Unknown reference selection')
    native.require(set(selection['tasks']) == set(TASK_IDS), 'Selection must name all four tasks')
    selected_ids = list(task_ids or TASK_IDS)
    native.require(len(set(selected_ids)) == len(selected_ids) and set(selected_ids) <= set(TASK_IDS), 'Invalid selected tasks')
    native.require(inspection is not None or set(selected_ids) == set(TASK_IDS), 'Partial review cannot issue gate')
    selected = {task: selection['tasks'][task] for task in selected_ids}
    native.require(all(isinstance(binding, dict) for binding in selected.values()), 'Selected reference binding is not ready')
    native.require(set(selection['original_fixture_manifests']) == {'stdlib', 'aws'}, 'Both original fixture manifests required')
    for pin in selection['original_fixture_manifests'].values():
        native.require(native.sha(read(pin['path'], pins)) == pin['sha256'], 'Original fixture manifest changed')
    for path in [EXPERIMENT / 'common/guard.py', EXPERIMENT / 'common/review_native.py',
                 *sorted(HERE.glob('*.py')), HERE / 'copy-provenance.json', *sorted((HERE / 'origins').glob('*.py'))]:
        read(path.relative_to(EXPERIMENT).as_posix(), pins)
    denied_runs, denied_raw, denied_observations = exclusions(selection, selected, pins)
    cache, results, errors = {}, {}, {}
    for task_id, binding in selected.items():
        task_pins = {}
        try:
            result = inspect_task(task_id, binding, denied_runs, denied_raw, cache, task_pins)
            results[task_id] = (result, task_pins)
        except (native.EvidenceError, ValueError, KeyError, OSError) as error:
            errors[task_id] = dict(type=type(error).__name__, reason=str(error), qualified_success=False)
        pins.update(task_pins)
    destination = HERE / 'reviews' / inspection if inspection else HERE
    native.require(inspection is None or native.safe_path(inspection) and '/' not in inspection, 'Bad inspection name')
    if errors:
        write(destination / 'failed-reference-review.json', dict(status='FAIL', all_references_match=False,
            tasks_failed=errors, successful_tasks=list(results), input_files=pins, model_calls=0,
            new_native_calls=0, reference_gate_issued=False))
        raise native.EvidenceError('Reference mapping failed; no gate issued: ' + repr(errors))
    tasks = {}
    for task_id, ((profile, mapped, report), task_pins) in results.items():
        binding = selected[task_id]
        profile_path = destination / 'profiles' / (task_id + '.json')
        mapping_path = destination / 'mappings' / (task_id + '.json')
        replay_path = destination / 'replays' / (task_id + '.json')
        for path, value in ((profile_path, profile), (mapping_path, mapped), (replay_path, report)):
            write(path, value)
            relative = path.relative_to(EXPERIMENT).as_posix()
            task_pins[relative] = pins[relative] = native.sha(path.read_bytes())
        for path in [binding['edit_profile'], binding['inherited_profile'], binding['fixture_manifest'],
                     *binding['base_sources'].values()]:
            task_pins[path] = pins[path]
        tasks[task_id] = dict(reference_case_id=binding['case_id'], qualified_success=True,
            native_profile=dict(path=profile_path.relative_to(EXPERIMENT).as_posix(), sha256=native.sha(profile_path.read_bytes())),
            edit_profile=dict(path=binding['edit_profile'], sha256=pins[binding['edit_profile']]),
            base_sources={name: dict(path=path, sha256=pins[path]) for name, path in binding['base_sources'].items()},
            inherited_unit_count=report['inherited_unit_count'], named_units=report['named_units'],
            actual_target_units=report['actual_target_units'], input_files=dict(sorted(task_pins.items())))
    summary = dict(schema='repodisco-varied-growth-reference-gate-v1', status='INSPECTION_ONLY' if inspection else 'PASS',
        all_references_match=not inspection and set(tasks) == set(TASK_IDS), tasks=tasks,
        original_fixture_manifests=selection['original_fixture_manifests'], input_files=dict(sorted(pins.items())),
        excluded_analyst_observations=denied_observations, ineligible_parent_runs=denied_runs,
        ineligible_parent_raw_fingerprints=denied_raw, actual_observations_replayed=len(tasks),
        model_calls=0, new_native_calls=0, execution_release_issued=False,
        negative_controls_release='pending separate source-bound review',
        independent_manual_review='pending root review', unlogged_definitions_are_not_passes=True)
    if not inspection:
        native.require(set(tasks) == set(TASK_IDS) and all(t['qualified_success'] for t in tasks.values()),
                       'All four references must qualify before gate issuance')
    write(destination / ('inspection.json' if inspection else 'reference-gate.json'), summary)
    print(json.dumps(dict(status=summary['status'], task_units={k: v['named_units'] for k, v in tasks.items()},
                          all_references_match=summary['all_references_match'], model_calls=0)))
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--selection', type=Path, required=True)
    parser.add_argument('--tasks', nargs='+', choices=TASK_IDS)
    parser.add_argument('--inspection')
    args = parser.parse_args()
    run(args.selection, args.tasks, args.inspection)
