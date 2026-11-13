"""Combine reviewed byte-identical observations and audit named-target scope offline."""
from pathlib import Path
import hashlib,json,csv,io
import target_metrics as m
ROOT=Path(__file__).resolve().parent
REV=ROOT/'revision-003'
load=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n')

def assemble():
    reports={ROOT:load(ROOT/'results-review.json'),REV:load(REV/'results-review.json')}
    assert reports[REV]['all_expected']
    for path in reports:
        assert reports[path]['reviewer_sha256']==sha(path/'review.py')
        for n,h in load(path/'verification-001-sha256.json').items():assert sha(path/'verification-001'/n)==h
        for n,h in load(path/'manifest.json').items():assert sha(path/n)==h
    current=load(REV/'all-cases.json');rows=[];evidence={}
    for case in current:
        source=REV if case['task_id'].startswith('excluded_witness') else ROOT
        record=next(x for x in reports[source]['checks'] if x['case_id']==case['case_id'])
        assert record['matched'] and record['source_sha256']==case['source_sha256']
        assert {p.name:sha(p) for p in (REV/case['path']).glob('*.dfy')}==case['source_sha256']
        path=source/'verification-001'/(case['case_id']+'.json');raw=load(path)
        assert raw['source_sha256']==case['source_sha256'] and sha(path)==record['evidence_sha256']
        evidence[case['case_id']]=raw
        rows.append(dict(**case,evidence_path=str(path.relative_to(ROOT)),evidence_sha256=sha(path),
            job_id=reports[source]['job_id'],review_path=str((source/'results-review.json').relative_to(ROOT)),
            review_sha256=sha(source/'results-review.json'),reused_unchanged_observation=(source==ROOT)))
    scopes={};measurements=[]
    for task in load(REV/'tasks.json'):
        tid=task['task_id'];ref=evidence[tid+'-reference'];units={}
        for text in ref['csv'].values():
            reader=csv.DictReader(io.StringIO(text));assert reader.fieldnames==m.HEADER
            for r in reader:
                match=m.NAME.fullmatch(r[m.HEADER[0]]);assert match
                name,kind,batch=match.groups();units.setdefault(name,set()).add(kind)
        scope=dict(expected_units={n:sorted(k) for n,k in sorted(units.items())},
            editable_targets=['HelperA.Prove']+(['HelperB.Prove'] if task['sharing']=='separate' else []),
            target_dependencies={'HelperA.Prove':[],'HelperB.Prove':['HelperA.Prove'] if task['sharing']=='shared' else [],
                'ClientA.Target':['HelperA.Prove'],'ClientB.Target':['HelperB.Prove']},
            recursion='Self-recursion, where present, is checked within each named lemma; it is not a cross-target graph edge.')
        scopes[tid]=scope
        for variant in ('reference','alternative','faulty'):
            raw=evidence[tid+'-'+variant];metrics=m.scores(raw['csv'],scope,units)
            assert metrics['supplied_providers_verified']
            if variant=='faulty':
                assert metrics['editable_local']['passed']==0 and metrics['supplied_clients_closed']['passed']==0
            else:
                assert metrics['editable_local']['passed']==len(task['editable_files']) and metrics['supplied_clients_closed']['passed']==2
            measurements.append(dict(case_id=tid+'-'+variant,**metrics))
    gate=dict(current_sources='revision-003',model_calls=0,all_expected=True,planned_controls=36,
        positive_controls=12,ordinary_proof_failures=22,termination_failures=2,
        reused_unchanged_observations=24,new_observations=12,unique_repair_seeds=6,
        failed_history_preserved=['verification-001 excluded-witness controls','revision-002/verification-001 frontend failures'],
        checks=rows,source_manifest_sha256=sha(REV/'manifest.json'),assembler_sha256=sha(Path(__file__)))
    save(ROOT/'validation-gate.json',gate)
    save(ROOT/'measurement-scope.json',dict(interpreter_sha256=sha(ROOT/'target_metrics.py'),tasks=scopes,control_measurements=measurements))
    print(json.dumps({k:v for k,v in gate.items() if k!='checks'},indent=2))

if __name__=='__main__':assemble()
