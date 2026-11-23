"""Replay fixed analyst controls against the reviewed reference inventories.

This does not create profiles, promote candidates or change any model score.
Helper-mutated and omitted-source workspaces remain analyst trust controls.
"""
import argparse
import copy
import json
from pathlib import Path
import re

import collect
import native_scorer as scorer
import ops

ROOT=Path(__file__).resolve().parent


def materialize_control_profile(profile,case,metadata,sources):
    current=copy.deepcopy(profile)
    inputs=current.get('verification_inputs')
    ops.require(isinstance(inputs,list) and set(inputs)==set(sources), 'Qualified source inventory differs')
    prefix=current['command'][:-len(inputs)]
    ops.require(current['command'][-len(inputs):]==inputs, 'Qualified command inputs differ')
    current['command']=prefix+case['command_files']
    omitted=set(sources)-set(case['command_files'])
    ops.require(omitted==set(metadata.get('omit_from_command',[])), 'Control omission differs')
    if omitted:current.pop('verification_inputs')
    else:current['verification_inputs']=case['command_files']
    changed=[]
    for entry in current['unlogged_definitions']:
        file=entry['file'];actual=scorer.sha(sources[file])
        if actual!=entry['source_sha256']:
            line=entry.get('source_line')
            ops.require(isinstance(line,str) and line.strip() in sources[file].decode('utf-8'),
                        'An unlogged declaration itself changed; manual review required')
            changed.append(dict(name=entry['name'],file=file,
                reference_source_sha256=entry['source_sha256'],control_source_sha256=actual,
                frozen_fixture_identity_required=True,counted_as_pass=False))
            entry['source_sha256']=actual
    return current,changed


def named_outcomes(report,name):
    return [row['outcome'] for row in report['units'] if row['name'].startswith(name+' (')]


def expectation(report,metadata,profile,raw):
    intended=metadata['expected_category']
    required_failed=metadata.get('expected_failed_targets',[])
    required_passed=metadata.get('expected_passed_targets',[])
    inspect=metadata.get('inspect_targets',[])
    failed_named=all('Failed' in named_outcomes(report,name) for name in required_failed)
    passed_named=all(named_outcomes(report,name) and set(named_outcomes(report,name))=={'Passed'}
                     for name in required_passed)
    allowed_failures=required_failed+inspect
    unexpected_failed=[row['name'] for row in report['units'] if row['outcome']=='Failed'
        and not any(row['name'].startswith(name+' (') for name in allowed_failures)]
    text=raw['stdout.txt'].decode()+'\n'+raw['stderr.txt'].decode()
    expected_missing=sorted(label for label,file in profile['required_units'].items()
                            if file in metadata.get('omitted_source_all_units',[]))
    if intended=='PROOF_PASS':
        matched=report['qualified_success'] and passed_named
    elif intended=='PROOF_FAILURE':
        matched=(report['category']=='PROOF_FAILURE' and bool(required_failed) and failed_named
                 and passed_named and not unexpected_failed and report['proof_coverage_complete'])
    elif intended=='COVERAGE_OMISSION':
        matched=(report['category']=='COVERAGE_FAILURE' and report['missing_units']==expected_missing
                 and bool(expected_missing) and not report['extra_units'] and report['failed_units']==0
                 and all(row['outcome']=='Passed' for row in report['units'])
                 and report['summaries']==[(report['passed_units'],0)]
                 and report['resources']['exit_status']==0 and report['warning_policy_matches']
                 and not re.search(r'\bError\s*:',text,re.I))
    else:raise ValueError('Unknown fixed control expectation')
    return dict(expected_category=intended,expected_match=bool(matched),
        expected_failed_targets=required_failed,expected_passed_targets=required_passed,
        inspect_targets={name:named_outcomes(report,name) for name in inspect},
        failed_targets_match=failed_named,passed_targets_match=bool(passed_named),
        unexpected_failed_units=unexpected_failed,expected_omitted_units=expected_missing)


def review_case(case,metadata,folder,profile,profile_pin,job):
    workspace=ops.regular_files(folder/'workspace')
    sources={name:data for name,data in workspace.items() if name.endswith('.dfy')}
    source_hashes=scorer.check_sources(sources)
    ops.require(source_hashes==case['source_sha256'], 'Frozen control source differs')
    record=ops.read(folder/'record.json');raw=ops.regular_files(folder/'raw')
    ops.require(record.get('run_id')==job+':'+case['id']
                and record.get('host',{}).get('job_id')==job
                and record['host'].get('cpus_per_task')==1, 'Exact native control job differs')
    current,unlogged_changes=materialize_control_profile(profile,case,metadata,sources)
    pins=scorer.EvidencePins(profile_sha256=scorer.sha(scorer.canonical(current)),
        record_sha256=scorer.sha(scorer.canonical(record)),
        source_revision_sha256=scorer.sha(scorer.canonical(source_hashes)),
        raw_sha256=tuple(sorted(scorer.hashes(raw).items())),run_id=job+':'+case['id'],
        origin='analyst_qualification')
    report=scorer.review(current,sources,record,raw,pins)
    return dict(case_id=case['id'],task_id=case['task_id'],reference_profile=profile_pin,
        materialized_profile=current,unlogged_source_bindings=unlogged_changes,
        observation=report,expectation=expectation(report,metadata,current,raw),
        model_acceptance=False,acceptance_issued=False)


def review(project):
    selected,freeze_path,frozen=ops.identity(project)
    binding,gate=collect.validate_reference_gate(ROOT.parent,ROOT)
    archive=ROOT/f'retrieved-{project}';receipt=ops.read(ROOT/f'transfer-{project}.json')
    inventory={name:dict(bytes=len(data),sha256=ops.sha(data))
               for name,data in sorted(ops.regular_files(archive).items())}
    ops.require(inventory==receipt['files'], 'Retrieved archive differs from transfer inventory')
    job=receipt['job_id']
    ops.require(ops.submitted_job(project)==job and ops.read(archive/'submission.json').get('job_id')==job,
                'Exact control submission differs')
    terminal=ops.terminal_accounting((archive/'accounting.txt').read_text(),job)
    ops.require(ops.sha((archive/selected['freeze']).read_bytes())==ops.sha(freeze_path.read_bytes()),
                'Archived control freeze differs')
    config=collect.validate_config(ops.read(ROOT/'configs'/f'{project}.json'))
    metadata={entry['id']:entry for entry in ops.read(ROOT/'control-metadata'/f'{project}.json')['cases']}
    results=[];missing=[]
    for case in config['cases']:
        folder=archive/'qualification-002'/f'output-{project}'/case['id']
        if not (folder/'record.json').is_file():missing.append(case['id']);continue
        entry=binding['tasks'][case['task_id']]
        profile=ops.read(ROOT.parent/entry['profile_path'])
        results.append(review_case(case,metadata[case['id']],folder,profile,
            dict(path=entry['profile_path'],sha256=entry['profile_sha256']),job))
    return dict(schema='dafny-growth-controls-review-v1',project=project,job_id=job,
        freeze_sha256=ops.sha(freeze_path.read_bytes()),reference_gate_sha256=binding['gate_sha256'],
        terminal_accounting=terminal,observations=results,missing_records=missing,
        all_expected_match=not missing and all(row['expectation']['expected_match'] for row in results),
        model_calls=0,acceptance_issued=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project',choices=('stdlib','aws'));parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();result=review(args.project);ops.save(args.output,result)
    print(json.dumps(dict(project=args.project,cases=len(result['observations']),
        all_expected_match=result['all_expected_match'],missing=result['missing_records'])))
