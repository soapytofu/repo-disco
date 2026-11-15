"""Replay edit boundaries and review saved diagnostics without any verification."""
from pathlib import Path
import json
import prepare as p
import preflight as v
ROOT=Path(__file__).resolve().parent

def primary_preservation(root=ROOT,primary=None):
    prov=p.validate_inputs(root)
    experiments=root.parents[1] if root.name=='runtime-002' else root.parent
    primary=primary or experiments/prov['parent_pilot']/prov['parent_archive']
    manifest=p.load(root/'primary-archive-manifest.json')
    actual={x.relative_to(primary).as_posix():p.sha(x) for x in primary.rglob('*') if x.is_file()}
    assert actual==manifest,'Original primary archive differs'
    for name,item in prov['parent_copies'].items():assert (root/name).read_bytes()==(primary/item['primary_path']).read_bytes()
    return dict(original_archive_files_preserved=len(manifest),exact_parent_copies=len(prov['parent_copies']),
                primary_score_unchanged='27/32',model_calls=0)

def review(root=ROOT,primary=None,*,write=True,allow_fake=False):
    preserved=primary_preservation(root,primary);generated=p.candidates(root);cases={c['case_id']:c for c,_,_ in generated if c['admitted']}
    out=root/'verification-001';pins=p.load(root/'manifest.json');assert pins==p.load(out/'manifest.json')
    for name,h in pins.items():assert p.sha(root/name)==p.sha(out/name)==h,name
    env=p.load(out/'environment.json')
    assert allow_fake or env.get('offline_fake') is False
    assert env['job_id'] and 'login' not in env['host'].lower() and env['model_calls']==0
    assert env['dafny']==v.TOOLCHAIN and env['z3']==v.Z3
    summary=p.load(out/'summary.json');assert summary['planned']==len(cases)==5 and summary['completed']==len(summary['results'])
    scope=p.load(root/'frozen-001/measurement-scope.json');seen=set();rows=[]
    for row in summary['results']:
        cid=row['case_id'];assert cid not in seen;seen.add(cid);case=cases[cid]
        assert row==p.load(out/(cid+'.json')) and row['parent_trial']==case['parent_trial']
        assert p.hashes(p.files(out/case['path']))==row['source_sha256']==case['source_sha256']
        assert row['command']==v.COMMAND and row['attempts']==1 and row['model_calls']==0
        assert row['category']==v.classify(row,case['expected_verified_obligations'])
        metrics=v.measured(row,scope['tasks'][case['task_id']],case['expected_verified_obligations'])
        assert row['target_metrics']==metrics and row['matched']==(row['category']=='strict_success' and not row.get('measurement_failed',False))
        csv={x.relative_to(out/'raw-csv'/cid).as_posix():x.read_bytes().decode() for x in (out/'raw-csv'/cid).rglob('*') if x.is_file()}
        assert csv==row['csv'] and {n:p.digest(t.encode()) for n,t in csv.items()}==row['csv_sha256']
        rows.append(dict(case_id=cid,parent_trial=case['parent_trial'],semantic_instance=case['semantic_instance'],sharing=case['sharing'],
            analyst_strict_success=row['matched'],category=row['category'],exit_code=row['exit_code'],
            verified_obligations=case['expected_verified_obligations'] if row['matched'] else None,source_sha256=case['source_sha256'],
            evidence_sha256=p.sha(out/(cid+'.json')),new_lemma_calls=0,primary_outcome_unchanged='PROOF_FAILURE'))
    complete=seen==set(cases);assert summary['all_expected']==(complete and all(r['analyst_strict_success'] for r in rows))
    report=dict(job_id=env['job_id'],complete=complete,all_expected=summary['all_expected'],cases=len(cases),
        analyst_strict_successes=sum(r['analyst_strict_success'] for r in rows),checks=rows,**preserved,
        protected_files=sum(c['protected_file_comparisons'] for c in cases.values()),
        protected_body_boundaries=sum(c['protected_body_boundaries'] for c in cases.values()),
        offline_fake=env.get('offline_fake',False),
        limitation='Post-hoc analyst sufficiency check: no new model attempts, model successes, minimality, causal effects or primary rescoring.')
    if write:
        p.save(root/'results-review.json',report)
        p.save(root/'verification-001-sha256.json',{x.relative_to(out).as_posix():p.sha(x) for x in out.rglob('*') if x.is_file()})
    return report

if __name__=='__main__':
    result=review();print(json.dumps(result,indent=2))
    if not result['complete'] or not result['all_expected']:raise SystemExit('Diagnostic incomplete or failed; preserve evidence')
