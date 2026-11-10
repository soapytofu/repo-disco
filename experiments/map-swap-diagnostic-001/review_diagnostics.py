"""Reproduce the cross-run preservation review; no verifier or model dispatch."""
import importlib.util
import json
from pathlib import Path
import re
from prepare import sha, load

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent.parent
PILOT=ROOT.parent/'varied-calibration-pilot-001'

def inventory(root):return {str(p.relative_to(root)):sha(p) for p in root.rglob('*') if p.is_file()}

def review():
    original=load(ROOT/'original-pilot-sha256.json')
    assert inventory(PILOT)==original
    pins=load(ROOT/'original-input-sha256.json')
    for name,h in pins.items():assert sha(REPO/name)==h,name
    for a,b in [('varied-cal-05','varied-cal-24'),('varied-cal-15','varied-cal-30')]:
        first=PILOT/'model-001'/a;second=PILOT/'model-001'/b
        assert inventory(first/'candidate')==inventory(second/'candidate')
        left=load(first/'response.json');right=load(second/'response.json')
        assert left['text']==right['text'] and left['request_id']!=right['request_id']
    source=ROOT.parent/'varied-calibration-001/protocol'
    assert (ROOT/'policy/old_body_guard.py').read_bytes()==(source/'body_guard.py').read_bytes()
    assert (ROOT/'policy/extract_response.py').read_bytes()==(source/'extract_response.py').read_bytes()
    spec=importlib.util.spec_from_file_location('frozen_preservation_guard',ROOT/'policy/old_body_guard.py')
    guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)
    fixed=boundaries=transfers=0;rows=[]
    for version in [ROOT,ROOT/'revision-002']:
        out=version/'verification-001';manifest=load(version/'manifest.json')
        assert load(out/'manifest.json')==manifest
        for name,h in manifest.items():assert sha(version/name)==sha(out/name)==h,name
        for name,h in load(version/'transfer.json')['files'].items():assert sha(version/name)==h;transfers+=1
        assert inventory(out)==load(version/'verification-001-sha256.json')
        env=load(out/'environment.json');summary=load(out/'summary.json');checks=load(version/'checks.json')
        assert summary['planned']==summary['completed']==len(summary['results'])==len(checks)
        assert env['model_calls']==0 and 'login' not in env['host']
        assert env['dafny']=='4.11.0+fcb2042d6d043a2634f0854338c08feeaaaf4ae2'
        assert env['z3']=='Z3 version 4.12.1 - 64 bit'
        for check,row in zip(checks,summary['results']):
            seed=version/'seed' if version!=ROOT else ROOT/'seeds'/check['task_id']
            task=load(version/'task.json') if version!=ROOT else next(t for t in load(ROOT/'tasks.json') if t['task_id']==check['task_id'])
            for p in seed.glob('*.dfy'):
                actual=(out/check['path']/p.name).read_text();text=p.read_text()
                if p.name in task['editable_files']:
                    a,b=guard.split_seed(text);assert actual.startswith(a) and actual.endswith(b);boundaries+=1
                else:assert actual==text;fixed+=1
            path=out/(check['task_id']+'-'+check['variant']+'.json');assert load(path)==row
            assert row['attempts']==1 and row['model_calls']==0
            assert row['command']==['timeout','-k','5s','60s','dafny','verify','--verify-included-files','All.dfy']
            assert {p.name:sha(p) for p in (out/check['path']).glob('*.dfy')}==row['source_sha256']==check['source_sha256']
            if check['variant']=='quantifier_false_control':
                assert row['exit_code']==2 and row['diagnostic']=='parse_error' and not row['matched'];continue
            assert row['matched'] and row['exit_code'] in (0,4)
            text=row['stdout']+'\n'+row['stderr'];warnings=len(re.findall(r': Warning:',text))
            if row['exit_code']==0:assert warnings==0 and '0 errors' in text
            rows.append(dict(variant=check['variant'],job_id=env['job_id'],evidence=str(path.relative_to(ROOT)),
                evidence_sha256=sha(path),source_sha256=check['source_sha256'],expected=row['expected'],
                diagnostic=row['diagnostic'],exit_code=row['exit_code'],warnings=warnings,reused_prior_observation=version==ROOT))
    assert len(rows)==6 and sum(r['exit_code']==0 for r in rows)==3
    return dict(new_model_calls=0,original_primary_score='27/32 unchanged',original_pilot_files_unchanged=len(original),
        original_parent_inputs_unchanged=len(pins),transferred_files_checked=transfers,current_logical_checks=6,
        current_matched=6,total_actual_verifier_invocations=7,reused_first_run_observations=5,strict_diagnostic_passes=3,
        expected_proof_failures=3,retired_malformed_control=dict(job_id='59527654',exit_code=2,diagnostic='parse_error',
        binder='fresh',evidence='verification-001/map_swap-shallow-separate-quantifier_false_control.json'),
        protected_file_checks_all_invocations=fixed,body_boundary_checks_all_invocations=boundaries,
        original_policy_unchanged=True,rows=rows)

if __name__=='__main__':
    report=review()
    assert report==load(ROOT/'diagnostic-review.json'),'Published combined review mismatch'
    print(json.dumps({k:v for k,v in report.items() if k not in ('rows','retired_malformed_control')},indent=2))
