"""Offline exact-source/raw-evidence and named-target review; never runs Dafny.

This file is outside the immutable verifier manifests. Output is a new sibling
review directory; unexpected mathematical outcomes are reported, never relabeled.
"""
import argparse
import base64
from collections import Counter
import csv
import hashlib
import importlib.util
import io
import json
from pathlib import Path, PurePosixPath
import re

ROOT=Path(__file__).resolve().parent
RUNTIME_SHA='3936dde3b081c0a9a216eec426f8dc165b9f28ac5a8d8d9b0d6a368eef0ea98d'
FIXTURE_SHA='bf3bd3618edd19acd9727e0646c1779082eff811f6f99efb06c7ff1090a0eabf'
TARGETS={'Helper.Transfer','Client.Target'}
HEADER=['TestResult.DisplayName','TestResult.Outcome','TestResult.Duration','TestResult.ResourceCount','RandomSeed']
# Same Dafny logger-name grammar as the pinned target_metrics.py interpreter;
# this study deliberately has no assumed WF/correctness unit count.
NAME=re.compile(r'([A-Za-z_][A-Za-z_0-9]*(?:\.[A-Za-z_][A-Za-z_0-9]*)+) \((correctness|well-formedness)\)(?: \(assertion batch ([1-9][0-9]*)\))?')
DURATION=re.compile(r'(?:[0-9]+\.)?[0-9]{2}:[0-5][0-9]:[0-5][0-9](?:\.[0-9]+)?')


def require(value,message):
    if not value:raise ValueError(message)


def sha(raw):return hashlib.sha256(raw).hexdigest()


def pairs(rows):
    value={}
    for key,item in rows:
        require(key not in value,'Duplicate JSON key')
        value[key]=item
    return value


def load(path):
    def reject(value):raise ValueError('Nonstandard JSON')
    return json.loads(Path(path).read_bytes(),object_pairs_hook=pairs,parse_constant=reject)


def safe(root,name):
    require(isinstance(name,str) and name and '\\' not in name,'Relative POSIX path required')
    rel=PurePosixPath(name)
    require(not rel.is_absolute() and all(p not in ('','.','..') for p in name.split('/')),'Unsafe path')
    path=Path(root)
    require(path.is_dir() and not path.is_symlink(),'Regular root required')
    for piece in rel.parts:
        path/=piece;require(not path.is_symlink(),'Symlink forbidden')
    return path


def inventory(root):
    require(root.is_dir() and not root.is_symlink(),'Regular evidence directory required')
    result={}
    for path in sorted(root.rglob('*')):
        require(not path.is_symlink() and (path.is_file() or path.is_dir()),'Nonregular evidence')
        if path.is_file():result[path.relative_to(root).as_posix()]=sha(path.read_bytes())
    return result


def source_scope(files,task,case,reference):
    require(set(files)=={'All.dfy','Client.dfy','Helper.dfy','Kernel.dfy'},'Exact four-file workspace required')
    require({n:sha(b) for n,b in files.items()}==case['source_sha256'],'Fixture bytes differ')
    require(files['Kernel.dfy']==reference['Kernel.dfy'] and files['All.dfy']==reference['All.dfy'],'Immutable provider/include changed')
    public=task['public_contract_prefix'].encode()
    require(files['Client.dfy'].startswith(public) and sha(public)==task['public_contract_sha256']==case['public_contract_sha256'],
            'Public contract prefix changed')
    internal=task['internal_api_versions'][case['internal_api_version']]
    require(sha(internal['header'].encode())==internal['sha256'] and files['Helper.dfy'].startswith(internal['header'].encode()+b'  {\n'),
            'Unplanned helper contract')
    for name in ('Client.dfy','Helper.dfy'):
        boundary=case['body_boundaries'][name];raw=files[name];start,end=boundary['start'],boundary['end']
        require(type(start) is int and type(end) is int and 0<=start<=end<=len(raw),'Invalid body boundary')
        require(raw[:start].endswith(b'  {\n') and raw[end:]==b'  }\n}\n','Body scope changed')
        require(sha(raw[:start]+b'<BODY>\n'+raw[end:])==boundary['protected_sha256'],'Protected boundary changed')
        if name=='Client.dfy':require(raw[:start]==public,'Public boundary differs')
    declarations={}
    for filename,raw in files.items():
        text=raw.decode('utf-8');modules=re.findall(r'^module ([A-Za-z_][A-Za-z_0-9]*) \{',text,re.M)
        if filename=='All.dfy':require(not modules,'Unexpected include-host declaration');continue
        require(len(modules)==1,'One fixed module per file required')
        for kind,name in re.findall(r'^  (method|function) ([A-Za-z_][A-Za-z_0-9]*)\(',text,re.M):
            symbol=modules[0]+'.'+name
            require(symbol not in declarations,'Duplicate source declaration')
            declarations[symbol]=kind
    require({n:k for n,k in declarations.items() if k=='method'}==dict.fromkeys(TARGETS,'method'),'Unexpected method scope')
    return declarations


def named_units(csv_files,declarations):
    require(isinstance(csv_files,dict) and csv_files,'Missing CSV evidence')
    units={};parts={};batches={}
    for filename,text in csv_files.items():
        require(isinstance(text,str),'CSV text required')
        reader=csv.DictReader(io.StringIO(text,newline=''),strict=True)
        require(reader.fieldnames==HEADER,'Malformed CSV header')
        for row in reader:
            require(set(row)==set(HEADER) and all(isinstance(v,str) for v in row.values()),'Malformed CSV row')
            name=row[HEADER[0]];match=NAME.fullmatch(name)
            require(match is not None and name not in units,'Malformed or duplicate unit')
            symbol,kind,batch=match.groups()
            require(symbol in declarations,'Unrecognized declaration evidence')
            require(row[HEADER[1]] in ('Passed','Failed'),'Unresolved unit outcome')
            require(DURATION.fullmatch(row[HEADER[2]]) is not None and row[HEADER[3]].isdigit() and row['RandomSeed']=='0',
                    'Malformed logger metadata')
            units[name]=row[HEADER[1]]
            parts.setdefault(symbol,set()).add(kind)
            batches.setdefault((symbol,kind),[]).append(None if batch is None else int(batch))
    require(set(parts)==set(declarations),'Missing declaration evidence')
    require(all('correctness' in parts.get(target,set()) for target in TARGETS),'Missing method correctness evidence')
    for indices in batches.values():
        require(indices==[None] if None in indices else sorted(indices)==list(range(1,len(indices)+1)),
                'Missing or mixed assertion batches')
    local={target:all(outcome=='Passed' for name,outcome in units.items() if NAME.fullmatch(name)[1]==target)
           for target in sorted(TARGETS)}
    failed_provider_units=[name for name,outcome in units.items() if NAME.fullmatch(name)[1] not in TARGETS and outcome!='Passed']
    return dict(units=units,observed_unit_kinds={n:sorted(k) for n,k in sorted(parts.items())},
                local_targets=local,failed_targets=[n for n,p in local.items() if not p],
                unverified_providers=failed_provider_units,providers_verified=not failed_provider_units)


def raw_evidence(out,case,record):
    paths=set();rawdir=out/'raw'/case['case_id']
    for stream in ('stdout','stderr'):
        raw=base64.b64decode(record[stream+'_base64'],validate=True)
        require(sha(raw)==record[stream+'_sha256'] and raw.decode('utf-8',errors='replace')==record[stream], 'Raw stream/base64/hash mismatch')
        path=safe(out,'raw/'+case['case_id']+'/'+stream+'.txt')
        require(path.read_bytes()==raw,'Raw stream archive mismatch');paths.add(path.relative_to(out).as_posix())
    require(set(record['csv'])==set(record['csv_base64'])==set(record['csv_sha256']),'CSV inventory mismatch')
    for name,value in record['csv_base64'].items():
        raw=base64.b64decode(value,validate=True)
        require(sha(raw)==record['csv_sha256'][name] and raw.decode('utf-8',errors='replace')==record['csv'][name], 'CSV/base64/hash mismatch')
        path=safe(out,'raw/'+case['case_id']+'/csv/'+name)
        require(path.read_bytes()==raw,'Raw CSV archive mismatch');paths.add(path.relative_to(out).as_posix())
    return paths


def audit(root,out):
    root=Path(root);out=Path(out)
    require(sha((root/'runtime-manifest.json').read_bytes())==RUNTIME_SHA and
            sha((root/'fixture-manifest.json').read_bytes())==FIXTURE_SHA,'Pinned verifier/fixture manifest changed')
    pins={}
    for filename in ('runtime-manifest.json','fixture-manifest.json'):
        for name,h in load(root/filename).items():
            require(name not in pins or pins[name]==h,'Conflicting source pins')
            require(sha(safe(root,name).read_bytes())==h,'Pinned source changed: '+name);pins[name]=h
    spec=importlib.util.spec_from_file_location('internal_propagation_frozen_verifier',root/'verify.py')
    verifier=importlib.util.module_from_spec(spec);spec.loader.exec_module(verifier)
    require(verifier.validate_pins(root)==pins,'Verifier pin set differs')
    actual_inventory=inventory(out);claimed=load(out/'evidence-manifest.json')
    require({n:h for n,h in actual_inventory.items() if n!='evidence-manifest.json'}==claimed,'Complete archive inventory mismatch')
    archived_pins=dict(pins,**{'runtime-manifest.json':RUNTIME_SHA})
    for name,h in archived_pins.items():require(sha(safe(out,name).read_bytes())==h,'Archived input changed: '+name)
    expected_paths=set(archived_pins)|{'environment.json','summary.json','evidence-manifest.json'}
    env=load(out/'environment.json')
    require(env['model_calls']==0 and str(env['job_id']).isdigit() and 'login' not in env['host'].lower()
            and env['partition'] in ('test','shared','sapphire'),'Compute provenance mismatch')
    require(env['runtime_manifest_sha256']==RUNTIME_SHA and env['fixture_manifest_sha256']==FIXTURE_SHA,'Run pin binding mismatch')
    for program,version in [('dafny',verifier.DAFNY_VERSION),('z3',verifier.Z3_VERSION)]:
        record=env[program];require(record['exit_code']==0 and record['stdout'].strip()==version,'Tool version mismatch')
        for stream in ('stdout','stderr'):
            name=program+'-version.'+stream;expected_paths.add(name)
            require((out/name).read_bytes().decode(errors='replace')==record[stream],'Tool version raw bytes mismatch')
    submission=root/'submission-001.json'
    if submission.exists():
        submitted=load(submission);require(str(submitted['job_id'])==str(env['job_id']),'Submission job differs')
        require(submitted['no_requeue'] is True and 'PreemptMode=OFF' in submitted['live_partition'],'Submission policy differs')
        require(submitted['runtime_manifest_sha256']==RUNTIME_SHA and submitted['fixture_manifest_sha256']==FIXTURE_SHA,'Submission pins differ')
    cases=load(root/'cases.json');tasks={t['task_id']:t for t in load(root/'tasks.json')}
    require(len(cases)==18 and len({c['case_id'] for c in cases})==18 and len(tasks)==2,'Exact planned cases required')
    summary=load(out/'summary.json')
    require(summary['planned']==18 and summary['completed']==18 and summary['model_calls']==0,'Incomplete run')
    require([r['case_id'] for r in summary['checks']]==[c['case_id'] for c in cases],'Case order/coverage mismatch')
    rows=[];coarse_matches=[];source_count=public_count=provider_count=boundary_count=0
    for case,coarse in zip(cases,summary['checks']):
        files={p.name:p.read_bytes() for p in safe(root,case['path']).glob('*.dfy')}
        reference={p.name:p.read_bytes() for p in (root/'fixtures'/case['task_id']/'reference').glob('*.dfy')}
        declarations=source_scope(files,tasks[case['task_id']],case,reference)
        source_count+=len(files);public_count+=1;provider_count+=1;boundary_count+=2
        for name,raw in files.items():require(safe(out,case['path']+'/'+name).read_bytes()==raw,'Archived workspace differs')
        path=out/(case['case_id']+'.json');record=load(path);expected_paths.add(path.name)
        require(record['command']==verifier.COMMAND and record['attempts']==1 and record['model_calls']==0,'Verifier command/attempt mismatch')
        require(record['source_sha256']==case['source_sha256'] and record['case_id']==case['case_id'],'Verifier source binding mismatch')
        expected_paths.update(raw_evidence(out,case,record))
        actual=verifier.classify(record);coarse_match=verifier.matches(case,record);details=verifier.diagnostic_details(record)
        # The JSON serialization of summary tuples is an array; normalize both.
        normalized=json.loads(json.dumps(details))
        require(record['diagnostics']==normalized and record['actual']==coarse['actual']==actual,'Diagnostic/category drift')
        require(record['matched']==coarse['matched']==coarse_match and record['expected']==coarse['expected']==case['expected'],
                'Coarse expectation changed')
        require(record['expected_diagnostic']==coarse['expected_diagnostic']==case['expected_diagnostic'] and
                coarse['diagnostic_categories']==details['diagnostic_categories'],'Expected diagnostic changed')
        require(coarse['evidence_sha256']==sha(path.read_bytes()),'Case evidence hash mismatch')
        coarse_matches.append(coarse_match)
        try:
            named=named_units(record['csv'],declarations)
            scope_error=None
        except (ValueError,csv.Error) as error:
            named=None;scope_error=str(error)
        expected_targets=case['expected_local_targets']
        require(set(expected_targets)==TARGETS and all(type(v) is bool for v in expected_targets.values()) and
                sorted(case['expected_failed_targets'])==sorted(n for n,p in expected_targets.items() if not p),'Invalid target expectations')
        named_match=named is not None and named['local_targets']==expected_targets and named['providers_verified']
        if named is not None:
            consistent=(all(v=='Passed' for v in named['units'].values()) if actual=='success' else
                        any(v=='Failed' for v in named['units'].values()) if actual=='proof_failure' else False)
        else:consistent=False
        rows.append(dict(case_id=case['case_id'],task_id=case['task_id'],variant=case['variant'],expected=case['expected'],
            actual=actual,coarse_expected_match=coarse_match,strict_workspace_verified=actual=='success',
            expected_local_targets=expected_targets,named_scope_valid=named is not None,named_scope_error=scope_error,
            named_evidence=named,named_expected_match=named_match,logger_category_consistent=consistent,
            matched=coarse_match and named_match and consistent,evidence_sha256=sha(path.read_bytes())))
    require(summary['all_expected']==all(coarse_matches),'Runner aggregate differs')
    require(set(actual_inventory)==expected_paths,'Unexpected/missing raw archive file')
    require(inventory(out)==actual_inventory,'Evidence changed while reviewing')
    return dict(schema='repodisco-internal-contract-named-review-v1',job_id=env['job_id'],model_calls=0,
        planned=18,reviewed=len(rows),all_expected=all(r['matched'] for r in rows),counts=dict(Counter(r['actual'] for r in rows)),
        source_files_checked=source_count,public_contract_prefixes_checked=public_count,
        immutable_kernel_comparisons=provider_count,body_boundaries_checked=boundary_count,
        archived_input_files=len(archived_pins),raw_archive_files=len(actual_inventory),
        reference_units={r['case_id']:r['named_evidence'] for r in rows if r['variant'] in ('reference','paired_repair','alternative')},
        checks=rows,claim='Verifier-only evidence for chosen internal API migrations; no model result, repair minimality or necessary multi-file edit claim'),actual_inventory


def review(root=ROOT,out=None,destination=None):
    root=Path(root).resolve();out=Path(out or root/'verification-001').resolve()
    destination=Path(destination or root/'reviews/review-001').resolve()
    require(not destination.exists() and not destination.is_relative_to(out),'New review outside raw evidence required')
    result,pins=audit(root,out)
    destination.mkdir(parents=True,exist_ok=False)
    for name,value in [('results-review.json',result),('evidence-sha256.json',pins)]:
        with (destination/name).open('x') as stream:json.dump(value,stream,indent=2);stream.write('\n')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence',type=Path,default=ROOT/'verification-001')
    parser.add_argument('--output',type=Path,default=ROOT/'reviews/review-001')
    args=parser.parse_args();result=review(out=args.evidence,destination=args.output)
    print(json.dumps({k:v for k,v in result.items() if k not in ('checks','reference_units')},indent=2))
    raise SystemExit(0 if result['all_expected'] else 1)
