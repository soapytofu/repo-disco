"""Review this separate analyst diagnostic without altering original pilot scores."""
import json
import re
from pathlib import Path
import prepare as p

ROOT=Path(__file__).resolve().parent

def review():
    out=ROOT/'verification-001';pins=p.load(out/'manifest.json')
    assert pins==p.load(ROOT/'manifest.json')
    for n,h in pins.items():assert p.sha(out/n)==p.sha(ROOT/n)==h,n
    env=p.load(out/'environment.json')
    assert env['model_calls']==0 and 'login' not in env['host']
    assert env['dafny']=='4.11.0+fcb2042d6d043a2634f0854338c08feeaaaf4ae2'
    cases=p.load(out/'cases.json');summary=p.load(out/'summary.json')
    assert summary['planned']==summary['completed']==len(summary['results'])==len(cases)==4
    generated={case['case_id']:fs for case,fs in p.candidates()}
    rows=[]
    for case,raw in zip(cases,summary['results']):
        assert raw==p.load(out/(case['case_id']+'.json')) and raw['case_id']==case['case_id']
        assert p.files(out/case['path'])==generated[case['case_id']]
        assert raw['source_sha256']==case['source_sha256']==p.hashes(p.files(out/case['path']))
        assert raw['model_calls']==0 and raw['attempts']==1
        assert raw['command']==['timeout','-k','5s','60s','dafny','verify','--verify-included-files','--log-format','csv','All.dfy']
        for n,t in raw['csv'].items():
            assert (out/'raw-csv'/case['case_id']/n).read_bytes()==t.encode()
            assert p.hashlib.sha256(t.encode()).hexdigest()==raw['csv_sha256'][n]
        text=raw['stdout']+'\n'+raw['stderr']
        warnings='warning' in text.lower()
        errors=re.findall(r'^(\w+\.dfy)\(\d+,\d+\): Error: (.+)$',text,re.M)
        if case['expected_exit']==0:
            matched=raw['exit_code']==0 and '20 verified, 0 errors' in text and not warnings and not errors
        else:
            matched=(raw['exit_code']==4 and '19 verified, 1 error' in text and not warnings and
                     errors==[('HelperA.dfy','a precondition for this call could not be proved')])
        rows.append(dict(case_id=case['case_id'],parent_trial=case['parent_trial'],
            expected_exit=case['expected_exit'],actual_exit=raw['exit_code'],matched=matched,
            original_body_policy_admitted=case['original_body_policy_admitted'],
            source_sha256=raw['source_sha256'],diagnostics=errors,warnings=warnings))
    original=ROOT.parent/'map-development-pilot-001'
    inventory=p.load(original/'model-001-sha256.json')
    for n,h in inventory.items():assert p.sha(original/'model-001'/n)==h,n
    for tid in ['map-dev-04','map-dev-08','map-dev-09']:
        for name in ['task.json','trial.json','response.json','extraction.json']:
            assert (ROOT/'parents'/tid/name).read_bytes()==(original/'model-001'/tid/name).read_bytes()
    report=dict(job_id=env['job_id'],model_calls=0,all_expected=all(x['matched'] for x in rows),
        checks=rows,prior_model_archive_files_preserved=len(inventory),
        prior_score_unchanged=True,reviewer_sha256=p.sha(Path(__file__)),
        limitation='Analyst sufficiency check, not a new model success, minimality result or rescoring')
    (ROOT/'results-review.json').write_text(json.dumps(report,indent=2)+'\n')
    (ROOT/'verification-001-sha256.json').write_text(json.dumps({str(x.relative_to(out)):p.sha(x) for x in sorted(out.rglob('*')) if x.is_file()},indent=2)+'\n')
    print(json.dumps(report,indent=2))
    if not report['all_expected']:raise SystemExit('Unexpected diagnostic; preserve evidence before any deliberate revision')

if __name__=='__main__':review()
