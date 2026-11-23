"""Read-only qualification inventory review; never issues a native profile.

New labels are taken only from the retained CSV, not inferred from declarations.
The source-bound inherited unit maps are fixed prior evidence. New coverage and
unlogged declarations still require root's manual review before qualification.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import re

import collect
import native_scorer as scorer
import ops

ROOT=Path(__file__).resolve().parent


def select_inherited(project,case):
    ops.require(project=='stdlib', 'This revision has no AWS review/dispatch')
    name='stdlib-stage1.json' if 'growth/AppendAll.dfy' in case['source_sha256'] else 'stdlib-stage0.json'
    path=ROOT/'inherited-profiles'/name
    return ops.read(path),dict(path='qualification-004/inherited-profiles/'+name,sha256=ops.sha(path.read_bytes()))


def review_case(config,case,folder,annotation,inherited,inherited_pin,job):
    sources=ops.regular_files(folder/'workspace')
    sources={name:data for name,data in sources.items() if name.endswith('.dfy')}
    source_hashes=scorer.check_sources(sources)
    record_bytes=(folder/'record.json').read_bytes();record=json.loads(record_bytes)
    raw=ops.regular_files(folder/'raw');raw_hashes=scorer.hashes(raw)
    ops.require(source_hashes==case['source_sha256'] and record.get('source_before_sha256')==source_hashes
                and record.get('source_after_sha256')==source_hashes, 'Exact candidate source evidence differs')
    ops.require(record.get('schema')=='dafny-library-native-record-v1'
                and record.get('origin')=='analyst_qualification'
                and record.get('attempts')==1 and record.get('model_calls')==0
                and record.get('run_id')==job+':'+case['id']
                and record.get('host',{}).get('job_id')==job
                and record['host'].get('cpus_per_task')==1
                and 'login' not in record['host'].get('hostname','').lower(), 'Native provenance differs')
    expected_argv=[config['dafny'],'verify']+config['options']+case['command_files']
    ops.require(record.get('argv')==expected_argv and set(case['command_files'])==set(sources),
                'Native explicit scope or command differs')
    ops.require(record.get('toolchain')==inherited['toolchain']
                and record.get('toolchain_after')==inherited['toolchain'], 'Native tool identity differs')
    ops.require({'stdout.txt','stderr.txt','resources.txt'}<=set(raw)
                and all(name in {'stdout.txt','stderr.txt','resources.txt'}
                    or name.startswith('csv/') and name.endswith('.csv') for name in raw)
                and record.get('raw_sha256')==raw_hashes, 'Full raw evidence differs')
    rows=scorer._csv(inherited,raw)
    resources=scorer._resources(raw['resources.txt'])
    units={row['name']:row['outcome'] for row in rows}
    inherited_units=inherited['required_units']
    ops.require(set(inherited_units.values())<=set(sources), 'Inherited scope is absent')
    missing=sorted(set(inherited_units)-set(units))
    failed_inherited={name:units[name] for name in inherited_units if name in units and units[name]!='Passed'}
    new_rows=[row for row in rows if row['name'] not in inherited_units]
    text=raw['stdout.txt'].decode('utf-8')+'\n'+raw['stderr.txt'].decode('utf-8')
    warnings=re.findall(r'^.*\bWarning\s*:[^\n]*$',text,re.I|re.M)
    warning_counts=[int(n) for n in re.findall(r'\b(\d+) warnings?\b',text,re.I)]
    warning_count=max([len(warnings)]+warning_counts)
    errors=re.findall(r'^.*\bError\s*:[^\n]*$',text,re.I|re.M)
    summaries=[(int(a),int(b)) for a,b in scorer.SUMMARY.findall(text)]
    passed=sum(outcome=='Passed' for outcome in units.values())
    failed=sum(outcome=='Failed' for outcome in units.values())
    nonfinal=[name for name,outcome in units.items() if outcome not in {'Passed','Failed'}]
    code=record.get('exit_code')
    category='UNKNOWN_NATIVE_FAILURE'
    if record.get('timeout') or code==124:category='TIMEOUT'
    elif code is None or code<0 or code in {137,143}:category='PROCESS_FAILURE'
    elif re.search(r'(?:Error:.*(?:timed out|time limit)|\b[1-9]\d* time outs?\b)',text,re.I):
        category='VERIFIER_TIMEOUT'
    elif re.search(r'(?:Error:.*(?:out of resource|resource limit|out of memory)|OutOfResource)',text,re.I) or nonfinal:
        category='RESOURCE_FAILURE'
    elif re.search(r'\bparse errors? detected\b',text,re.I):category='FRONTEND_PARSE_FAILURE'
    elif re.search(r'\bresolution/type errors? detected\b',text,re.I):category='FRONTEND_RESOLUTION_FAILURE'
    elif not resources['complete'] or resources['exit_status']!=code:category='RESOURCE_OBSERVATION_MISMATCH'
    elif missing:category='INHERITED_COVERAGE_FAILURE'
    elif len(summaries)!=1 or summaries[0][0]!=passed:category='SUMMARY_INVENTORY_MISMATCH'
    elif code==4 and summaries[0][1]>0 and failed and errors:category='PROOF_FAILURE'
    elif summaries[0][1]==0 and failed==0 and not errors and code in {0,2}:
        if code==2 and warning_count:category='WARNING_ONLY'
        elif code==0:category='NATIVE_SUCCESS_INVENTORY_PENDING'
    declared=list(dict.fromkeys(annotation.get('required_targets',[])+annotation.get('new_fixed_declarations',[])))
    observations={name:[row for row in rows if row['name'].startswith(name+' (')] for name in declared}
    inherited_unlogged=[dict(entry,current_source_sha256=source_hashes[entry['file']],
        current_declaration_review_pending=source_hashes[entry['file']]!=entry['source_sha256'])
        for entry in inherited['unlogged_definitions']]
    new_unlogged=[dict(name=name,actual_native_units=[],counted_as_pass=False,declaration_review_pending=True)
                  for name,observed in observations.items() if not observed]
    return dict(case_id=case['id'],task_id=case['task_id'],job_id=job,category=category,
        qualified_success=False,acceptance_issued=False,native_inventory_qualified=False,
        complete_new_declaration_inventory_requires_manual_review=True,
        source_sha256=source_hashes,source_revision_sha256=scorer.sha(scorer.canonical(source_hashes)),
        record_sha256=ops.sha(record_bytes),raw_sha256=raw_hashes,toolchain=record['toolchain'],
        inherited_profile=inherited_pin,inherited_expected_units=inherited_units,
        missing_inherited_units=missing,nonpassing_inherited_units=failed_inherited,
        exact_rows=rows,new_observed_rows=new_rows,passed_units=passed,failed_units=failed,
        summaries=summaries,exit_code=code,timeout=record['timeout'],warnings=warnings,
        warning_count=warning_count,inherited_warning_policy_matches=warning_count==len(warnings)
            and Counter(warnings)==Counter(inherited['inherited_warnings']),
        errors=errors,resources=resources,elapsed_seconds=record['elapsed_seconds'],
        declared_target_observations=observations,inherited_unlogged_declarations=inherited_unlogged,
        new_declarations_without_logged_units=new_unlogged)


def review(project):
    selected,freeze_path,frozen=ops.identity(project)
    archive=ROOT/f'retrieved-{project}'
    receipt=ops.read(ROOT/f'transfer-{project}.json')
    members=ops.regular_files(archive)
    inventory={name:dict(bytes=len(data),sha256=ops.sha(data)) for name,data in sorted(members.items())}
    ops.require(inventory==receipt['files'], 'Retrieved archive differs from transfer inventory')
    job=receipt['job_id']
    ops.require(ops.submitted_job(project)==job and ops.read(archive/'submission.json').get('job_id')==job,
                'Archive/local exact submission differs')
    terminal=ops.terminal_accounting((archive/'accounting.txt').read_text(),job)
    ops.require(ops.sha((archive/selected['freeze']).read_bytes())==ops.sha(freeze_path.read_bytes()),
                'Archived runtime freeze differs')
    config=collect.validate_config(ops.read(ROOT/'configs'/f'{project}.json'))
    metadata=ops.read(ROOT/'reference-metadata'/f'{project}.json')
    annotations={entry['id']:entry for entry in metadata['references']}
    results=[];absent=[]
    for case in config['cases']:
        folder=archive/'qualification-004'/f'output-{project}'/case['id']
        if not (folder/'record.json').is_file():
            absent.append(case['id']);continue
        inherited,pin=select_inherited(project,case)
        results.append(review_case(config,case,folder,annotations[case['id']],inherited,pin,job))
    return dict(schema='dafny-growth-reference-inventory-review-v1',project=project,job_id=job,
        freeze_sha256=ops.sha(freeze_path.read_bytes()),terminal_accounting=terminal,
        archive_sha256=receipt['archive_sha256'],archive_members=len(inventory),observations=results,
        missing_case_records=absent,all_expected_records_present=not absent,
        native_inventory_qualified=False,acceptance_issued=False,model_calls=0)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project',choices=('stdlib',));parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();result=review(args.project);ops.save(args.output,result)
    print(json.dumps(dict(project=args.project,observations=len(result['observations']),
        categories={row['case_id']:row['category'] for row in result['observations']},
        missing=result['missing_case_records'],native_inventory_qualified=False)))
