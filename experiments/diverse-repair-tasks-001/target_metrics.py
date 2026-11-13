"""Offline interpretation of the pinned Dafny 4.11 diagnostic, not a rescoring tool."""
import csv
import hashlib
import io
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parent
HEADER=['TestResult.DisplayName','TestResult.Outcome','TestResult.Duration','TestResult.ResourceCount','RandomSeed']
NAME=re.compile(r'([A-Za-z_][A-Za-z_0-9]*(?:\.[A-Za-z_][A-Za-z_0-9]*)+) \((correctness|well-formedness)\)(?: \(assertion batch ([1-9][0-9]*)\))?')
EXPECTED={
    'Kernel.Move':{'well-formedness'},'Ops1.Certify':{'correctness'},
    'Ops2.MoveKeys':{'correctness'},'Ops2.MoveAt':{'correctness','well-formedness'},
    'Api.ObserveMove':{'correctness','well-formedness'},'Api.Equal':{'correctness','well-formedness'},
    'HelperA.Prove':{'correctness'},'HelperB.Prove':{'correctness'},
    'ClientA.Target':{'correctness'},'ClientB.Target':{'correctness','well-formedness'}}
RESTRICTION_EXPECTED={
    'Kernel.Merge':{'well-formedness'},'Kernel.Restrict':{'well-formedness'},
    'Ops1.Certify':{'correctness'},'Ops2.MergeKeys':{'correctness'},
    'Ops2.MergeAt':{'correctness','well-formedness'},'Ops2.RestrictKeys':{'correctness'},
    'Ops2.RestrictAt':{'correctness','well-formedness'},
    'Api.ObserveMerge':{'correctness','well-formedness'},'Api.ObserveRestrict':{'correctness','well-formedness'},
    'Api.Equal':{'correctness','well-formedness'},'HelperA.Prove':{'correctness'},'HelperB.Prove':{'correctness'},
    'ClientA.Target':{'correctness'},'ClientB.Target':{'correctness','well-formedness'}}


def sha(raw):return hashlib.sha256(raw).hexdigest()
def load(path):return json.loads(path.read_text())


def scores(csv_files,case,expected_units=None):
    expected_units=EXPECTED if expected_units is None else expected_units
    if not csv_files:raise ValueError('No logger evidence')
    seen=set();parts={};passed={};batches={}
    for text in csv_files.values():
        reader=csv.DictReader(io.StringIO(text))
        if reader.fieldnames!=HEADER:raise ValueError('Unexpected logger schema')
        for row in reader:
            if set(row)!=set(HEADER) or any(v is None for v in row.values()):raise ValueError('Malformed row')
            name=row[HEADER[0]];match=NAME.fullmatch(name)
            if not match or name in seen:raise ValueError('Unknown or duplicate verification unit')
            seen.add(name);symbol,kind,batch=match.groups()
            if row[HEADER[1]] not in ('Passed','Failed'):raise ValueError('Unresolved verifier outcome')
            if not row[HEADER[2]] or not row[HEADER[3]].isdigit() or row['RandomSeed']!='0':raise ValueError('Unexpected run metadata')
            parts.setdefault(symbol,set()).add(kind)
            passed.setdefault(symbol,[]).append(row[HEADER[1]]=='Passed')
            batches.setdefault((symbol,kind),[]).append(int(batch) if batch else None)
    if parts!=expected_units:raise ValueError('Missing, extra or misattributed declaration evidence')
    for values in batches.values():
        if None in values:
            if values!=[None]:raise ValueError('Mixed split and unsplit records')
        elif sorted(values)!=list(range(1,len(values)+1)):raise ValueError('Missing assertion batch')
    graph=case['target_dependencies']
    targets={'HelperA.Prove','HelperB.Prove','ClientA.Target','ClientB.Target'}
    if set(graph)!=targets or not set(case['editable_targets'])<=targets or len(set(case['editable_targets']))!=len(case['editable_targets']):
        raise ValueError('Target scope mismatch')
    state={}
    def visit(symbol):
        if symbol not in graph:raise ValueError('Missing dependency node')
        if state.get(symbol)==1:raise ValueError('Dependency cycle')
        if state.get(symbol)==2:return
        state[symbol]=1
        for dep in graph[symbol]:visit(dep)
        state[symbol]=2
    for symbol in graph:visit(symbol)
    local={symbol:all(passed[symbol]) for symbol in targets}
    support=all(all(v) for n,v in passed.items() if n not in targets)
    closed={}
    def close(symbol):
        if symbol not in closed:
            dependencies=[close(n) for n in graph[symbol]]
            closed[symbol]=support and local[symbol] and all(dependencies)
        return closed[symbol]
    for symbol in graph:close(symbol)
    editable=case['editable_targets'];clients=['ClientA.Target','ClientB.Target']
    return dict(logger_rows=len(seen),local_targets=dict(sorted(local.items())),
        dependency_closed_targets=dict(sorted(closed.items())),supplied_providers_verified=support,
        editable_local=dict(passed=sum(local[n] for n in editable),total=len(editable)),
        supplied_clients_local=dict(passed=sum(local[n] for n in clients),total=2),
        supplied_clients_closed=dict(passed=sum(closed[n] for n in clients),total=2),
        unit='One named lemma contract, all its logged obligations; not one CSV row or ensures clause')


def review():
    out=ROOT/'verification-001';manifest=load(out/'manifest.json')
    assert manifest==load(ROOT/'manifest.json')
    for name,h in manifest.items():assert sha((out/name).read_bytes())==h,name
    env=load(out/'environment.json');assert env['model_calls']==0 and 'login' not in env['host']
    assert env['dafny']=='4.11.0+fcb2042d6d043a2634f0854338c08feeaaaf4ae2'
    summary=load(out/'summary.json');cases=load(out/'cases.json')
    assert summary['planned']==summary['completed']==len(summary['results'])==len(cases)==4
    reports=[]
    for case,row in zip(cases,summary['results']):
        assert row['case_id']==case['case_id'] and row==load(out/(case['case_id']+'.json'))
        assert row['source_sha256']==case['source_sha256']
        assert {p.name:sha(p.read_bytes()) for p in (out/case['path']).glob('*.dfy')}==case['source_sha256']
        assert row['attempts']==1 and row['model_calls']==0
        assert row['command']==['timeout','-k','5s','60s','dafny','verify','--verify-included-files','--log-format','csv','All.dfy']
        assert row['exit_code']==case['expected_exit'] and row['matched']
        for name,text in row['csv'].items():
            assert (out/'raw-csv'/case['case_id']/name).read_text()==text
            assert sha(text.encode())==row['csv_sha256'][name]
        result=scores(row['csv'],case)
        assert result['local_targets']==case['expected_local']
        assert result['supplied_providers_verified'] and result['logger_rows']==14
        text=(row['stdout']+'\n'+row['stderr']).lower()
        assert 'warning' not in text and 'parse errors' not in text and 'resolution/type errors' not in text
        strict=row['exit_code']==0 and '0 errors' in text
        assert strict==(case['case_id']=='shared_reference')
        reports.append(dict(case_id=case['case_id'],source_sha256=case['source_sha256'],
            raw_evidence=str((out/(case['case_id']+'.json')).relative_to(ROOT)),
            strict_workspace_success=strict,**result))
    sub=ROOT/'restriction-001';arch=sub/'verification-001'
    pins=load(arch/'manifest.json');assert pins==load(sub/'manifest.json')
    for n,h in pins.items():assert sha((arch/n).read_bytes())==h,n
    subenv=load(arch/'environment.json');assert subenv['dafny']==env['dafny'] and 'login' not in subenv['host']
    case=load(arch/'cases.json')[0];record=load(arch/'restriction_reference.json')
    subsummary=load(arch/'summary.json')
    assert subsummary['completed']==subsummary['planned']==1 and subsummary['results']==[record]
    assert record['exit_code']==0 and record['model_calls']==0 and record['attempts']==1 and record['matched']
    assert record['source_sha256']==case['source_sha256']=={p.name:sha(p.read_bytes()) for p in (arch/case['path']).glob('*.dfy')}
    assert record['command']==summary['results'][0]['command']
    assert 'warning' not in (record['stdout']+record['stderr']).lower() and '20 verified, 0 errors' in record['stdout']
    for n,t in record['csv'].items():
        assert (arch/'raw-csv'/case['case_id']/n).read_text()==t and sha(t.encode())==record['csv_sha256'][n]
    compat=scores(record['csv'],case,RESTRICTION_EXPECTED)
    assert compat['logger_rows']==20 and compat['local_targets']==case['expected_local'] and compat['supplied_providers_verified']
    report=dict(job_id=env['job_id'],new_model_calls=0,cases=reports,
        restriction_compatibility=dict(job_id=subenv['job_id'],strict_workspace_success=True,
            source_sha256=record['source_sha256'],evidence='restriction-001/verification-001/restriction_reference.json',**compat),
        manifest_sha256=sha((out/'manifest.json').read_bytes()),
        analyst_controls=True,original_model_scores_unchanged=True,
        analysis_code_sha256=sha(Path(__file__).read_bytes()),
        limitation='Diagnostic of measurement on supplied analyst states; not evidence of model local-to-global performance')
    (ROOT/'target-review.json').write_text(json.dumps(report,indent=2)+'\n')
    (ROOT/'verification-001-sha256.json').write_text(json.dumps({str(p.relative_to(out)):sha(p.read_bytes()) for p in sorted(out.rglob('*')) if p.is_file()},indent=2)+'\n')
    for x in reports:print(x['case_id'],'editable',x['editable_local'],'closed clients',x['supplied_clients_closed'],'workspace',x['strict_workspace_success'])
    return report


if __name__=='__main__':review()
