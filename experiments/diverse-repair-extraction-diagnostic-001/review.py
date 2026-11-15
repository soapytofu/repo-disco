"""Reproduce exact extraction/guarded candidates and review all saved verifier evidence."""
from pathlib import Path
import json
import prepare as p
import preflight as v
ROOT=Path(__file__).resolve().parent

def primary_preservation(root=ROOT,primary=None):
    provenance=p.validate_inputs(root)
    original=primary or root.parent/provenance['parent_pilot']
    assert p.sha(original/'model-001-sha256.json')==provenance['primary_archive_manifest_sha256']
    assert p.sha(original/'reviewed-results.json')==provenance['primary_results_sha256']
    assert p.sha(original/'runtime-freeze.json')==provenance['primary_runtime_freeze_sha256']
    manifest=p.load(root/'primary-archive-manifest.json')
    for n,h in manifest.items():assert p.sha(original/'model-001'/n)==h,n
    for n,entry in provenance['parent_copies'].items():assert (root/n).read_bytes()==(original/'model-001'/entry['primary_path']).read_bytes(),n
    return dict(prior_archive_files_preserved=len(manifest),exact_parent_copies=len(provenance['parent_copies']),original_primary_score='16/24',prior_score_unchanged=True)

def review(root=ROOT,primary=None,write=True):
    preserved=primary_preservation(root,primary);out=root/'verification-001';pins=p.load(root/'manifest.json')
    assert pins==p.load(out/'manifest.json')
    for n,h in pins.items():assert p.sha(out/n)==p.sha(root/n)==h,n
    env=p.load(out/'environment.json')
    assert env['model_calls']==0 and env['job_id'] and 'login' not in env['host']
    assert env['dafny']==v.TOOLCHAIN and env['z3']==v.Z3
    generated=p.candidates(root);cases=[c for c,_,_ in generated];assert cases==p.load(out/'cases.json')
    expected={c['case_id']:(c,fs,payload) for c,fs,payload in generated if c['admitted']}
    summary=p.load(out/'summary.json');assert summary['model_calls']==0 and summary['planned']==len(expected) and summary['saved_responses']==8
    assert summary['completed']==len(summary['results'])
    rows=[];seen=set();scope=p.load(root/'frozen-001/measurement-scope.json')
    for raw in summary['results']:
        cid=raw['case_id'];assert cid not in seen;seen.add(cid);case,fs,payload=expected[cid]
        assert raw==p.load(out/(cid+'.json')) and raw['parent_trial']==case['parent_trial']
        assert p.files(out/case['path'])==fs and raw['source_sha256']==case['source_sha256']==p.hashes(fs)
        assert (out/case['payload_path']).read_bytes()==payload.encode()
        assert raw['model_calls']==0 and raw['attempts']==1 and raw['command']==v.COMMAND
        assert raw['category']==v.classify(raw)
        measured=v.measured(raw,scope['tasks'][case['task_id']]);assert measured==raw['target_metrics']
        csv={str(x.relative_to(out/'raw-csv'/cid)):x.read_bytes().decode() for x in (out/'raw-csv'/cid).rglob('*') if x.is_file()}
        assert csv==raw['csv'] and {n:p.digest(t.encode()) for n,t in csv.items()}==raw['csv_sha256']
        success=raw['category']=='strict_success' and measured['available'] and not raw.get('measurement_failed')
        rows.append(dict(case_id=cid,parent_trial=case['parent_trial'],sharing=case['sharing'],feedback_condition=case['feedback_condition'],
            strict_verified=success,category=raw['category'],actual_exit=raw['exit_code'],source_sha256=raw['source_sha256'],
            verified_obligations=11 if success else None,target_metrics=measured,body_rewriting=False,original_outcome='OUTPUT_REJECTED',
            diagnostic_evidence_sha256=p.sha(out/(cid+'.json'))))
    complete=seen==set(expected)
    assert summary['all_strict_verified']==all(x['strict_verified'] for x in rows)
    report=dict(job_id=env['job_id'],model_calls=0,complete=complete,guard_admitted=len(expected),saved_responses=8,
        strict_diagnostic_successes=sum(x['strict_verified'] for x in rows),all_strict_verified=complete and all(x['strict_verified'] for x in rows),
        unique_candidate_workspaces=len({tuple(sorted(c['source_sha256'].items())) for c in cases if c['admitted']}),
        protected_file_comparisons=sum(c.get('protected_files',0) for c in cases),protected_body_boundaries=sum(c.get('protected_body_boundaries',0) for c in cases),
        checks=rows,**preserved,reviewer_sha256=p.sha(root/'review.py'),
        limitation='Post-hoc extraction diagnostic of eight saved model responses; no fresh requests, proof edits, primary rescoring, general parser validation, causal effects or held-out claim.')
    if write:
        p.save(root/'results-review.json',report)
        p.save(root/'verification-001-sha256.json',{str(x.relative_to(out)):p.sha(x) for x in sorted(out.rglob('*')) if x.is_file()})
    return report

if __name__=='__main__':
    report=review();print(json.dumps(report,indent=2))
    if not report['complete'] or not report['all_strict_verified']:raise SystemExit('Diagnostic incomplete or proof failure; evidence preserved, no automatic retries')
