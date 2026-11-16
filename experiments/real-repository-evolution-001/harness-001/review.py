"""Offline source-linked review of native/adapter agreement; never reruns proofs."""
import base64
import json
from pathlib import Path
import sys
import dafny_gate as gate
from verify_controls import check_pins

ROOT=Path(__file__).resolve().parent

def review(output):
    check_pins()
    environment=json.loads((output/'environment.json').read_bytes())
    for label,expected in [('dafny',gate.DAFNY_VERSION),('z3',gate.Z3_VERSION)]:
        observed=environment['versions'][label]
        assert observed['exit_code']==0 and observed['stdout'].strip()==expected
    assert environment['runtime_sha256']==gate.sha((ROOT/'runtime-manifest.json').read_bytes())
    assert environment['fixture_sha256']==gate.sha((ROOT/'fixture-manifest.json').read_bytes())
    result=dict(model_calls=0,qualified_real_repositories=[],checks=[],issues=[],observations=[])
    for case in json.loads((ROOT/'controls.json').read_bytes())['cases']:
        folder=ROOT/case['path'];files={p.name:p.read_bytes() for p in folder.glob('*.dfy')}
        profile=json.loads((folder/'profile.json').read_bytes());scores={}
        for mode in ['native','adapter'] + (['entry_only'] if case['id']=='omitted_failure' else []):
            name=case['id']+'-'+mode;target=output/name
            try:
                record=json.loads((target/'record.json').read_bytes())
                assert json.loads((target/'profile.json').read_bytes())==profile
                assert {p.relative_to(target/'source').as_posix():p.read_bytes() for p in (target/'source').rglob('*.dfy')}==files
                raw={p.relative_to(target/'raw').as_posix():p.read_bytes() for p in (target/'raw').rglob('*') if p.is_file()}
                assert gate.hashes(raw)==record['raw_sha256']
                assert raw=={n:base64.b64decode(b,validate=True) for n,b in record['raw_base64'].items()}
                run_id=environment['job_id']+':'+name
                if mode=='entry_only':
                    assert record['run_id']==run_id and record['exit_code']==0
                    assert gate.SUMMARY.findall(raw['stdout.txt'].decode())==[('5','0')]
                    try:gate.score(files,profile,record,run_id)
                    except gate.GateError as exc:assert str(exc)=='Verification input command differs'
                    else:raise AssertionError('Incomplete command accepted')
                    result['checks'].append(dict(name=name,passed=True,outcome='Native entry-only passes; full-scope gate rejects omitted input.'))
                else:
                    scored=gate.score(files,profile,record,run_id)
                    scores[mode]=scored
                    assert scored['category']==case['expected'],scored
                    expected_code=0 if case['expected']=='VERIFIED' else 4 if case['expected']=='PROOF_FAILURE' else 2
                    assert record['exit_code']==expected_code
                    assert record['peak_rss_kib'] is not None and record['peak_rss_kib']>0
                    if case['id']=='helper_unproved':
                        assert scored['units']['Helper.Transfer (correctness)']=='Failed'
                        assert scored['units']['Client.Target (correctness)']=='Passed'
                    if case['id']=='client_unproved':
                        assert scored['units']['Helper.Transfer (correctness)']=='Passed'
                        assert scored['units']['Client.Target (correctness)']=='Failed'
                    if case['id']=='omitted_failure':assert scored['units']['Detached.Broken (correctness)']=='Failed'
                    result['checks'].append(dict(name=name,passed=True,outcome=scored['category']))
                    result['observations'].append(dict(name=name,**scored))
            except (AssertionError,gate.GateError,KeyError,ValueError,OSError) as exc:
                result['issues'].append(dict(name=name,error=str(exc)));result['checks'].append(dict(name=name,passed=False))
        if set(scores)=={'native','adapter'}:
            agreed=all(scores['native'][key]==scores['adapter'][key] for key in ['category','units','strict_success','warnings','proof_coverage_complete'])
            result['checks'].append(dict(name=case['id']+'-agreement',passed=agreed))
            if not agreed:result['issues'].append(dict(name=case['id'],error='Native/adapter disagreement'))
    result['accepted']=not result['issues'] and len(result['checks'])==22 and all(c['passed'] for c in result['checks'])
    return result

if __name__=='__main__':
    assert len(sys.argv)==3
    result=review(ROOT/sys.argv[1]);path=ROOT/sys.argv[2]
    with path.open('x') as file:json.dump(result,file,indent=2,sort_keys=True);file.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['checks','observations']}))
    sys.exit(0 if result['accepted'] else 1)
