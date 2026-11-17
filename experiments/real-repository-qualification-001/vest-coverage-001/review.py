"""Offline review of the exact Vest baseline and seven fresh coverage invocations."""
import json,re
from pathlib import Path
import protocol_v2 as g
ROOT=Path(__file__).resolve().parent
HELPER='vest_lib::core::proof::impl&%0::C::theorem_serialize_parse_roundtrip'
CLIENTS=['vest_dev::formats::dependent::'+n for n in ['explicit_length_roundtrip','inferred_length_roundtrip','explicit_tag_roundtrip','inferred_tag_roundtrip']]
SENTINEL='vest_dev::qualification_detached::omitted_failure'
def review():
 base=json.loads((ROOT/'profile.json').read_bytes());patches=json.loads((ROOT/'patches.json').read_bytes());job=json.loads((ROOT/'submission.json').read_bytes())['job_id']
 for n,h in json.loads((ROOT/'manifest.json').read_bytes()).items():assert g.sha((ROOT/n).read_bytes())==h,n
 for n,h in json.loads((ROOT/'transfer.json').read_bytes())['files'].items():assert g.sha((ROOT/n).read_bytes())==h,n
 for n,h in base['baseline_pins'].items():assert g.sha((ROOT.parent/n).read_bytes())==h,n
 out=ROOT/'results';assert (out/'complete.json').exists() and not (out/'failure.json').exists()
 assert json.loads((out/'environment.json').read_bytes())['manifest_sha256']==g.sha((ROOT/'manifest.json').read_bytes())
 nativeprefix=json.loads((ROOT.parent/base['baseline_phase']/'results/invocation-prefix.json').read_bytes())['prefix'];remote=Path(nativeprefix[-1]).parent.parent/ROOT.name
 observations={};summary={}
 for item in base['invocations']:
  label=item['id'];d=out/label;p=json.loads((d/'profile.json').read_bytes());r=json.loads((d/'bound-record.json').read_bytes());native=json.loads((d/'record.json').read_bytes())
  action='focus' if item['mode']=='client-focus-diagnostic' else 'verify'
  logical=['cargo','verus',action,'-p',item['package'],'--locked','--offline','--check-toolchain','--target-dir','<FRESH_TARGET>','--','--expand-errors','--output-json','--time-expanded','--num-threads','3']
  expected={**base,'case':item['case'],'mode':item['mode'],'package':item['package'],'logical_command':logical,'source_sha256':g.expected_files(base['source_sha256'],patches.get(item['case'],{})),'required':item['required']}
  assert p==expected,label
  prefix=list(nativeprefix);prefix[prefix.index('--pwd')+1]=str(remote/'work'/label);prefix[-1:-1]=['--env','CARGO_BUILD_JOBS=4']
  assert native['command']==prefix+[str(remote/'targets'/label) if x=='<FRESH_TARGET>' else x for x in logical]
  raw={n:(d/n).read_bytes() for n in ['stdout.txt','stderr.txt','resources.txt']}
  g.check_record(r,p,job+':'+label,raw)
  assert native['exit_code']==r['exit_code'] and native['elapsed_seconds']==r['elapsed_seconds'] and native['attempts']==1 and native['model_calls']==0
  assert native['artifacts']=={n:g.sha(b) for n,b in raw.items()}
  o=g.verus_observation(r['exit_code'],raw['stdout.txt'],raw['stderr.txt'],p['required'])
  o['full_dependency_command']=action=='verify';o['warnings_match_upstream']=sorted(o['warnings'])==sorted(base['upstream_warnings']);o['qualified_scope_pass']=o['proof_pass'] and action=='verify' and o['warnings_match_upstream']
  assert o==json.loads((d/'observation.json').read_bytes()),label
  observations[label]=o
  rss=re.search(r'Maximum resident set size \(kbytes\): (\d+)',raw['resources.txt'].decode())
  summary[label]={**{k:v for k,v in o.items() if k not in ('units','inventory','warnings')},'warning_count':len(o['warnings']),'timed_entries':sum(o['inventory'].values()),'friendly_labels':len(o['units']),'exit_code':r['exit_code'],'elapsed_seconds':r['elapsed_seconds'],'max_rss_kib':int(rss[1]) if rss else None}
 baseline=json.loads((ROOT/'native-vest_dev-observation.json').read_bytes());adapter=observations['baseline-adapter']
 assert adapter['qualified_scope_pass'] and adapter['units']==baseline['units'] and adapter['inventory']==baseline['inventory']
 assert {k:(s['verified'],s['errors']) for k,s in adapter['crates'].items()}=={k:(s['verified'],s['errors']) for k,s in baseline['crates'].items()}
 for label in ['broken-provider-native','broken-provider-adapter']:
  o=observations[label];assert o['category']=='PROOF_FAILURE' and not o['qualified_scope_pass'] and o['units'][HELPER] is False,label
 a=observations['broken-provider-native'];b=observations['broken-provider-adapter'];assert a['units']==b['units'] and a['inventory']==b['inventory']
 focus=observations['broken-provider-client-focus'];assert not focus['qualified_scope_pass'] and not focus['coverage_complete'] and HELPER not in focus['units']
 assert all(focus['units'].get(n) is True for n in CLIENTS),'Focus did not prove chosen clients'
 omitted=observations['detached-native-omitted'];assert summary['detached-native-omitted']['exit_code']==0 and omitted['category']=='PROVED_WITH_WARNINGS' and not omitted['coverage_complete'] and not omitted['qualified_scope_pass'] and SENTINEL not in omitted['units']
 for label in ['registered-native','registered-adapter']:
  o=observations[label];assert o['category']=='PROOF_FAILURE' and o['units'][SENTINEL] is False and not o['qualified_scope_pass'],label
 assert observations['registered-native']['units']==observations['registered-adapter']['units']
 return dict(status='QUALIFIED_FOR_DECLARED_PINNED_VEST_SCOPE',job_id=job,model_calls=0,new_invocations=7,reused_native_commands=2,scope=base['scope'],baseline_upstream_warnings=5,strict_zero_warning_root_baseline=False,native_adapter_agreements=['correct root and dependency baseline','broken provider','registered failing module'],coverage_controls=['Unproved provider rejects full scope','Focus-only passing clients cannot replace dependency proof','Omitted failing module rejected despite native exit zero','Registered failing module detected'],label_semantics='Friendly-name groups with exact multiplicity; not unique obligation IDs. Native verified totals are reported separately.',limitations='Upstream trust/external exemptions remain; default feature module trees only. Other workspace crates and unregistered files are outside the baseline scope. No model run or arbitrary model-edit handler.',observations=summary)
if __name__=='__main__':
 try:r=review()
 except Exception as e:
  with (ROOT/'review-001-failure.json').open('x') as f:json.dump(dict(type=type(e).__name__,message=str(e)),f,indent=2)
  raise
 with (ROOT/'review-001.json').open('x') as f:json.dump(r,f,indent=2,sort_keys=True);f.write('\n')
 print(json.dumps({k:v for k,v in r.items() if k!='observations'},indent=2))
