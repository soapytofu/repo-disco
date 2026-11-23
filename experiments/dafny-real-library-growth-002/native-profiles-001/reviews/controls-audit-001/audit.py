"""Independent read-only audit of the first 26 native control observations.

Read existing archives and replay their reviewer; additionally derive exact
inventory, named outcomes, omissions and classifications from raw CSV/diagnostics.
No native process, remote operation, model call, or release gate is produced.
"""
from collections import Counter
import csv
import io
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
EXPERIMENT = HERE.parents[2]
QUALIFICATION = EXPERIMENT / 'qualification-002'
sys.path.insert(0, str(QUALIFICATION))
import review as control_review
import native_scorer as scorer
import ops
sys.path.insert(0, str(EXPERIMENT / 'common'))
import guard

INPUTS = {}
BASE_MUTATIONS = {
    'splice-unproved-seed': ['growth/AppendAll.dfy'],
    'counted-unproved-frame': ['StandardLibrary/src/RepoDiscoU16Frame.dfy'],
    'tagged-unproved-pair': ['StandardLibrary/src/RepoDiscoFramePair.dfy'],
}
EXPECTED_MISSES = {'splice-no-tail-pop', 'splice-unproved-seed'}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def read(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink(), 'Missing/linked evidence: ' + str(path))
    raw = path.read_bytes()
    INPUTS[path.relative_to(EXPERIMENT).as_posix()] = scorer.sha(raw)
    return raw


def obj(path):
    return json.loads(read(path))


def named(units, name):
    return {label: outcome for label, outcome in units.items() if label.startswith(name + ' (')}


def main():
    gate = obj(EXPERIMENT / 'native-profiles-001/reference-gate.json')
    require(scorer.sha((EXPERIMENT / 'native-profiles-001/reference-gate.json').read_bytes()) ==
            '18888e38c1437b451595ff928a2c1ce1cd5908d405263ec54b46427e431d0b27', 'Reference gate changed')
    for name, digest in gate['input_files'].items():
        require(scorer.sha(read(EXPERIMENT / name)) == digest, 'Reference input drift: ' + name)
    for name in ['collect.py', 'review.py', 'native_scorer.py', 'ops.py', 'reference-gate-binding.json', 'tool-profiles.json']:
        read(QUALIFICATION / name)
    read(Path(__file__))
    read(EXPERIMENT / 'common/guard.py')
    observations, archive_audits = [], []
    for project in ('stdlib', 'aws'):
        recorded = obj(QUALIFICATION / 'reviews' / ('native-' + project + '-001.json'))
        replayed = control_review.review(project)
        require(scorer.canonical(recorded) == scorer.canonical(replayed), 'Saved control review no longer exactly replays')
        config = obj(QUALIFICATION / 'configs' / (project + '.json'))
        metadata = obj(QUALIFICATION / 'control-metadata' / (project + '.json'))
        case_catalog = obj(EXPERIMENT / metadata['source_path'])
        require(scorer.sha((EXPERIMENT / metadata['source_path']).read_bytes()) == metadata['source_sha256'], 'Case catalog drift')
        originals = {case['id']: case for case in case_catalog}
        controls = {case['id']: case for case in metadata['cases']}
        require(all(originals[key] == value for key, value in controls.items()), 'Expected control metadata was changed')
        fixture_root = (EXPERIMENT / metadata['source_path']).parent
        manifest = obj(fixture_root / 'manifest.json')
        transfer = obj(QUALIFICATION / ('transfer-' + project + '.json'))
        compressed = read(QUALIFICATION / ('transfer-' + project + '.tar.gz'))
        require(scorer.sha(compressed) == transfer['archive_sha256'] and len(compressed) == transfer['compressed_bytes'],
                'Compressed archive identity differs')
        archive = QUALIFICATION / ('retrieved-' + project)
        archive_files = ops.regular_files(archive)
        inventory = {name: dict(bytes=len(raw), sha256=scorer.sha(raw)) for name, raw in archive_files.items()}
        require(inventory == transfer['files'], 'Full unpacked transfer inventory differs')
        for name in archive_files:
            read(archive / name)
        read(QUALIFICATION / 'freezes' / (project + '.json'))
        read(QUALIFICATION / 'submissions' / (project + '.json'))
        archive_audits.append(dict(project=project, job_id=transfer['job_id'], files=len(inventory),
            compressed_bytes=len(compressed), archive_sha256=transfer['archive_sha256'],
            full_inventory_matches=True, exact_saved_review_replays=True,
            terminal_accounting=recorded['terminal_accounting']))
        saved = {row['case_id']: row for row in recorded['observations']}
        require(set(saved) == set(controls) and not recorded['missing_records'], 'Control observations missing/extra')
        for case in config['cases']:
            cid, task_id = case['id'], case['task_id']
            meta, saved_row = controls[cid], saved[cid]
            task = gate['tasks'][task_id]
            profile = obj(EXPERIMENT / task['native_profile']['path'])
            edit = obj(EXPERIMENT / task['edit_profile']['path'])
            folder = archive / 'qualification-002' / ('output-' + project) / cid
            record = obj(folder / 'record.json')
            sources = {name: read(folder / 'workspace' / name) for name in case['source_sha256']}
            require(scorer.hashes(sources) == case['source_sha256'] == meta['source_sha256'] ==
                    record['source_before_sha256'] == record['source_after_sha256'], 'Case source drift: ' + cid)
            require({name for name in ops.regular_files(folder / 'workspace') if name.endswith('.dfy')} == set(sources),
                    'Source inventory incomplete or has extra Dafny files')
            for name, raw in sources.items():
                fixture_path = EXPERIMENT / case['workspace_dir'] / name
                require(read(fixture_path) == raw, 'Observed source differs from exact fixture')
                require(manifest['files'][fixture_path.relative_to(fixture_root).as_posix()] == scorer.sha(raw),
                        'Fixture source lacks exact manifest pin')
            raw = {name: read(folder / 'raw' / name) for name in record['raw_sha256']}
            require(scorer.hashes(raw) == record['raw_sha256'], 'Raw evidence drift')
            require(set(ops.regular_files(folder / 'raw')) == set(raw), 'Extra or missing raw artifacts')
            expected_command = [config['dafny'], 'verify'] + config['options'] + case['command_files']
            require(record['argv'] == expected_command == meta['argv'], 'Exact native arguments differ')
            require(record['host']['job_id'] == transfer['job_id'] and record['host']['cpus_per_task'] == 1
                    and 'login' not in record['host']['hostname'].lower(), 'Wrong compute/CPU provenance')
            require(record['attempts'] == 1 and record['model_calls'] == 0 and not record['timeout']
                    and record['origin'] == 'analyst_qualification', 'Unexpected execution provenance')
            require(record['toolchain'] == record['toolchain_after'] == profile['toolchain'], 'Tool fingerprint drift')
            require(all(record['toolchain'][key] == value for key, value in config['expected_tool_fingerprint'].items()),
                    'Pinned tool package differs')
            rows = []
            for name, data in sorted(raw.items()):
                if not name.startswith('csv/'):
                    continue
                reader = csv.DictReader(io.StringIO(data.decode(), newline=''), strict=True)
                require(reader.fieldnames == profile['csv_columns'], 'CSV schema drift')
                rows.extend(list(reader))
            units = {row['TestResult.DisplayName']: row['TestResult.Outcome'] for row in rows}
            require(len(rows) == len(units) and rows, 'Duplicate/empty native inventory')
            require(all(row.get('RandomSeed', '0') == '0' and row['TestResult.ResourceCount'].isdigit()
                        for row in rows), 'Missing native unit metrics')
            require(units == {row['name']: row['outcome'] for row in saved_row['observation']['units']},
                    'Saved scorer inventory differs from direct CSV')
            omitted = set(sources) - set(case['command_files'])
            require(omitted == set(meta.get('omit_from_command', [])), 'Undeclared command omission')
            missing = set(profile['required_units']) - set(units)
            extra = set(units) - set(profile['required_units'])
            expected_missing = {label for label, file in profile['required_units'].items() if file in omitted}
            require(missing == expected_missing and not extra, 'Unexpected absent or extra obligations')
            inherited = {label for label, file in profile['required_units'].items() if file in task['base_sources']}
            require(len(inherited) == task['inherited_unit_count'] and inherited <= set(units), 'Inherited obligation missing')
            changed_base = sorted(name for name, pin in task['base_sources'].items()
                                  if scorer.sha(sources[name]) != pin['sha256'])
            require(changed_base == BASE_MUTATIONS.get(cid, []), 'Unplanned immutable-base mutation')
            allowed_failed = meta.get('expected_failed_targets', []) + meta.get('inspect_targets', [])
            inherited_nonpasses = {label: units[label] for label in sorted(inherited) if units[label] != 'Passed'}
            require(all(any(label.startswith(target + ' (') for target in allowed_failed)
                        for label in inherited_nonpasses), 'Unplanned inherited proof failure')
            prefix, suffix = guard._profile(edit)
            addition = sources[edit['addition']['path']]
            require(addition.startswith(prefix.encode()) and addition.endswith(suffix.encode()), 'Target contracts changed')
            body = addition[len(prefix.encode()):len(addition) - len(suffix.encode())].decode()
            base = {name: sources[name] for name in task['base_sources']}
            rejected_base = False
            try:
                rebuilt, _ = guard.reconstruct(edit, body, base, 'analyst-audit:' + cid)
                require(rebuilt == sources, 'Body guard reconstruction differs')
            except ValueError as error:
                require(bool(changed_base) and 'source identity differs' in str(error), 'Unexpected protected-edit rejection')
                rejected_base = True
            require(rejected_base == bool(changed_base), 'Mutated helper not rejected by model edit policy')
            text = raw['stdout.txt'].decode() + '\n' + raw['stderr.txt'].decode()
            warning_lines = re.findall(r'^.*\bWarning\s*:[^\n]*$', text, re.I | re.M)
            require(not warning_lines and not re.search(r'\b[1-9]\d* warnings?\b', text, re.I), 'New verifier warning')
            require(not re.search(r'\b(?:parse|resolution/type) errors? detected\b', text, re.I), 'Frontend failure')
            resource_failure = bool(re.search(r'\b(?:out of resource|out of memory|resource limit)\b', text, re.I))
            summary = re.findall(r'^Dafny program verifier finished with (\d+) verified, (\d+) errors?([^\n]*)$', text, re.M)
            require(len(summary) == 1, 'Missing/ambiguous summary')
            passed = sum(value == 'Passed' for value in units.values())
            failed = {label: value for label, value in units.items() if value != 'Passed'}
            require(int(summary[0][0]) == passed, 'Summary and exact CSV pass counts differ')
            resources = scorer._resources(raw['resources.txt'])
            require(resources['complete'] and resources['exit_status'] == record['exit_code'], 'Resource record incomplete')
            category = ('RESOURCE_FAILURE' if resource_failure else 'COVERAGE_FAILURE' if missing else
                        'VERIFIED' if record['exit_code'] == 0 and not failed and int(summary[0][1]) == 0 else
                        'PROOF_FAILURE' if record['exit_code'] == 4 and failed and int(summary[0][1]) > 0
                        and re.search(r'\bError\s*:', text) else 'UNCLASSIFIED')
            require(category == saved_row['observation']['category'], 'Independent raw classification differs')
            expected_failed = meta.get('expected_failed_targets', [])
            expected_passed = meta.get('expected_passed_targets', [])
            failed_targets_ok = all('Failed' in named(units, target).values() for target in expected_failed)
            passed_targets_ok = all(named(units, target) and set(named(units, target).values()) == {'Passed'}
                                    for target in expected_passed)
            unexpected_nonpasses = {label: value for label, value in failed.items()
                                    if not any(label.startswith(target + ' (') for target in allowed_failed)}
            intended = meta['expected_category']
            if intended == 'PROOF_FAILURE':
                matched = category == 'PROOF_FAILURE' and bool(expected_failed) and failed_targets_ok and passed_targets_ok and not unexpected_nonpasses and not missing
            elif intended == 'PROOF_PASS':
                matched = category == 'VERIFIED' and passed_targets_ok and not missing and not failed
            elif intended == 'COVERAGE_OMISSION':
                matched = category == 'COVERAGE_FAILURE' and bool(missing) and not failed and record['exit_code'] == 0 and int(summary[0][1]) == 0 and passed_targets_ok
            else:
                raise ValueError('Unknown frozen expected category')
            require(bool(matched) == saved_row['expectation']['expected_match'], 'Independent expectation match differs')
            observations.append(dict(case_id=cid, task_id=task_id, project=project, run_id=record['run_id'],
                expected_category=intended, actual_category=category, expected_match=bool(matched),
                native_exit=record['exit_code'], passed_units=passed, nonpassing_units=failed,
                source_sha256=scorer.hashes(sources), raw_sha256=scorer.hashes(raw),
                native_record_path=(folder / 'record.json').relative_to(EXPERIMENT).as_posix(),
                native_record_sha256=scorer.sha((folder / 'record.json').read_bytes()),
                inherited_unit_count=len(inherited), inherited_nonpasses=inherited_nonpasses,
                declared_targets={name:named(units, name) for name in meta['required_targets']},
                omitted_sources=sorted(omitted), missing_units=sorted(missing), extra_units=sorted(extra),
                all_staged_sources_hash_bound=True, changed_base_sources=changed_base,
                model_edit_policy_rejects_mutated_base=rejected_base,
                unknown_or_new_warnings=False, resources=resources,
                error_lines=re.findall(r'^.*\bError\s*:[^\n]*$', text, re.M),
                model_acceptance=False, acceptance_issued=False))
    misses = {row['case_id'] for row in observations if not row['expected_match']}
    require(misses == EXPECTED_MISSES and len(observations) == 26, 'Unexpected matched/missed control set')
    omissions = [row for row in observations if row['expected_category'] == 'COVERAGE_OMISSION']
    require(len(omissions) == 4 and all(row['expected_match'] for row in omissions), 'Missing omission control')
    helper_controls = {}
    for cid, parent, children in (
        ('counted-unproved-frame', 'RepoDiscoU16Frame.ReadU16Frame', ['RepoDiscoFrameBatch.ReadCountedFrames', 'RepoDiscoFramePair.ReadFramePair']),
        ('tagged-unproved-pair', 'RepoDiscoFramePair.ReadFramePair', ['RepoDiscoTaggedFramePair.ReadTaggedBoundedPair', 'RepoDiscoU16Frame.ReadU16Frame'])):
        row = next(row for row in observations if row['case_id'] == cid)
        require('Failed' in row['declared_targets'][parent].values(), 'Actual helper failure not observed')
        require(all(row['declared_targets'][child] and set(row['declared_targets'][child].values()) == {'Passed'}
                    for child in children), 'Actual caller/provider pass not observed')
        helper_controls[cid] = dict(actual_failed_parent=parent, actual_passing_children=children,
            observation_only_not_a_changed_prior_expectation=True, whole_workspace_acceptance=False)
    result = dict(schema='repodisco-growth-independent-controls-audit-v1',
        status='AUDIT_PASS_WITH_TWO_PRESERVED_UNMATCHED_CONTROLS', not_a_release_gate=True,
        observations=observations, archive_audits=archive_audits,
        total_observations=26, total_expected_matches=24, all_controls_match=False,
        matched_category_counts=dict(Counter(row['actual_category'] for row in observations if row['expected_match'])),
        unmatched_case_ids=sorted(misses), unmatched_categories={row['case_id']:row['actual_category'] for row in observations if not row['expected_match']},
        omission_controls={row['case_id']:dict(native_passed_units=row['passed_units'], exact_missing_units=row['missing_units']) for row in omissions},
        aws_actual_helper_failure_caller_pass=helper_controls,
        original_expectations_and_failure_evidence_unchanged=True,
        reference_gate_sha256='18888e38c1437b451595ff928a2c1ce1cd5908d405263ec54b46427e431d0b27',
        input_files=dict(sorted(INPUTS.items())), model_calls=0, new_native_calls=0, source_mutations=0,
        release_gate_issued=False, replacement_controls='Separate reviewed version; not part of this audit')
    with (HERE / 'audit.json').open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True);stream.write('\n')
    print(json.dumps({key:result[key] for key in ['status','total_observations','total_expected_matches','matched_category_counts','unmatched_case_ids','model_calls','new_native_calls']}))


if __name__ == '__main__':
    main()
