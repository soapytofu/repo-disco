"""Offline reconstruction and named-unit audit of the real VMC coverage controls."""
import csv,hashlib,json
from pathlib import Path
import protocol as g
R=Path(__file__).resolve().parent
CASES=[('vmc_baseline','adapter'),('vmc_broken_swap','native'),('vmc_broken_swap','adapter'),('vmc_detached','native-omitted'),('vmc_detached','adapter')]
def review():
    base=json.loads((R/'profile.json').read_bytes());patches=json.loads((R/'patches.json').read_bytes())
    for n,h in json.loads((R/'manifest.json').read_bytes()).items():assert g.sha((R/n).read_bytes())==h,n
    for n,h in json.loads((R/'transfer.json').read_bytes())['files'].items():assert g.sha((R/n).read_bytes())==h,n
    job=json.loads((R/'submission.json').read_bytes())['job_id'];out=R/'results';assert (out/'complete.json').exists() and not (out/'failure.json').exists()
    observations={}
    for case,mode in CASES:
        label=case+'-'+mode;folder=out/label
        p=json.loads((folder/'profile.json').read_bytes());record=json.loads((folder/'bound-record.json').read_bytes());native=json.loads((folder/'record.json').read_bytes())
        expected={**base,'case':case,'mode':mode,'source_sha256':g.expected_files(base['source_sha256'],patches.get(case,{}))}
        inputs=['dfyconfig.toml']+sorted(base['explicit_sources']+(['tests/QualificationDetached.dfy'] if case=='vmc_detached' else [])) if mode=='adapter' else base['native_inputs']
        expected['logical_command']=['verify',*inputs,'--resource-limit','20000','--log-format','csv']
        expected['required_units']=dict(base['required_units'])
        if case=='vmc_detached':expected['required_units']['QualificationDetached.Fails (correctness)']='tests/QualificationDetached.dfy'
        assert p==expected,label
        raw={n:(folder/n).read_bytes() for n in ['stdout.txt','stderr.txt','resources.txt']}
        raw.update({str(x.relative_to(folder)):x.read_bytes() for x in (folder/'csv').rglob('*.csv')})
        g.check_record(record,p,job+':'+label,raw)
        assert native['command'][-len(p['logical_command']):]==p['logical_command']
        assert native['exit_code']==record['exit_code'] and native['elapsed_seconds']==record['elapsed_seconds']
        for n,h in native['artifacts'].items():assert g.sha(raw[n])==h
        o=g.dafny_observation(record['exit_code'],raw['stdout.txt'],raw['stderr.txt'],{n:b for n,b in raw.items() if n.startswith('csv/')},p['required_units'])
        assert all(h==base['csv_header'] for h in o['csv_headers'])
        o['warnings_match_upstream']=sorted(o['warnings'])==sorted(base['upstream_warnings'])
        o['qualified_scope_pass']=o['proof_pass'] and o['warnings_match_upstream']
        saved=json.loads((folder/'observation.json').read_bytes());assert json.loads(json.dumps(o))==saved
        assert o['warnings_match_upstream'],label
        observations[label]=dict(o,exit_code=record['exit_code'],elapsed_seconds=record['elapsed_seconds'])
    baseline=json.loads((R/'vmc-native-baseline.json').read_bytes());adapter=observations['vmc_baseline-adapter']
    assert adapter['qualified_scope_pass'] and baseline['units']==adapter['units'] and baseline['category']==adapter['category']
    helper='FisherYates.Implementation.Trait.Swap (correctness)';client='FisherYates.Implementation.Trait.Shuffle (correctness)'
    for mode in ['native','adapter']:
        o=observations['vmc_broken_swap-'+mode]
        assert o['category']=='PROOF_FAILURE' and o['coverage_complete'] and not o['proof_pass']
        assert o['units'][helper]=='Failed' and o['units'][client]=='Passed'
    assert observations['vmc_broken_swap-native']['units']==observations['vmc_broken_swap-adapter']['units']
    omitted=observations['vmc_detached-native-omitted'];covered=observations['vmc_detached-adapter']
    sentinel='QualificationDetached.Fails (correctness)'
    assert omitted['exit_code']==0 and omitted['category']=='PROVED_WITH_WARNINGS' and not omitted['coverage_complete'] and not omitted['proof_pass'] and sentinel not in omitted['units']
    assert covered['category']=='PROOF_FAILURE' and covered['coverage_complete'] and covered['units'][sentinel]=='Failed' and not covered['proof_pass']
    summary={k:{a:b for a,b in v.items() if a!='units'} for k,v in observations.items()}
    return dict(status='QUALIFIED_FOR_DECLARED_PINNED_VMC_SCOPE',model_calls=0,job_id=job,new_invocations=5,reused_native_baselines=1,
      baseline_obligations=267,declared_source_files=28,files_with_logged_units=26,unlogged_files=base['unlogged_files'],
      upstream_trigger_warnings=3,strict_zero_warning_baseline=False,native_adapter_agreements=['correct baseline','broken Swap'],
      coverage_controls=['Passing Shuffle cannot hide failing Swap','Omitted failing module rejected despite native exit zero','Explicit failing module detected'],
      scope='Upstream pinned proof scope under existing trust exemptions; neither all code verified nor verifier soundness proved',observations=summary)
if __name__=='__main__':
    try:result=review()
    except Exception as e:
        with (R/'review-001-failure.json').open('x') as f:json.dump(dict(type=type(e).__name__,message=str(e)),f,indent=2)
        raise
    with (R/'review-001.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k!='observations'},indent=2))
