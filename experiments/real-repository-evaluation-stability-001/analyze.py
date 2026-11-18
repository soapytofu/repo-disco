"""Post-run analysis of reviewed CSV resource counts; no verifier calls."""
import csv,json,re
from pathlib import Path
import common as c
import review
from capture import write

TARGETS=[
 'FisherYates.Model.Swap (well-formedness)',
 'FisherYates.Correctness.InductionHypothesisPrecondition1 (correctness)',
 'FisherYates.Correctness.ProbabilityOfE (correctness)',
]

def analyze():
    c.validate_package()
    native_review=review.review_verification('dafny-vmc')
    transfer=c.read(c.ROOT/'transfer-dafny-vmc.json');c.check_pins(c.ROOT,transfer['files'])
    parent=c.read(c.ROOT/'preserve-parents.json');c.check_pins(c.ROOT.parent.parent,parent['files'])
    cases=[];out=c.ROOT/'verification-dafny-vmc-001'
    for entry in c.read(c.ROOT/'plan.json')['cases']:
        d=out/('slot-%02d'%entry['slot']);observed=c.read(d/'observation.json');native=c.read(d/'record.json')
        units={}
        for path in sorted((d/'csv').rglob('*.csv')):
            for row in csv.DictReader(path.open(newline='')):
                name=row['TestResult.DisplayName'];c.require(name not in units,'Duplicate unit')
                units[name]=dict(outcome=row['TestResult.Outcome'],resource_count=int(row['TestResult.ResourceCount']),
                                 duration=row['TestResult.Duration'])
        text=(d/'stdout.txt').read_text()+'\n'+(d/'stderr.txt').read_text()
        limited=re.findall(r'Verification out of resource \(([^\n]+)\)\s*$',text,re.M)
        for name,item in units.items():item['resource_limited']=name in limited
        c.require(set(units)==set(observed['units']),'Resource/proof inventory differs')
        c.require(all(item['outcome']==observed['units'][n] for n,item in units.items()),'CSV result differs')
        c.require(all(n in units and units[n]['outcome']=='Failed' for n in limited),'Resource target differs')
        cases.append(dict(slot=entry['slot'],source=entry['source'],resource_limit=entry['resource_limit'],
                          candidate_sha256=entry['candidate_sha256'],exit_code=native['exit_code'],
                          elapsed_seconds=native['elapsed_seconds'],category=observed['category'],
                          proof_complete=observed['proof_pass'],qualified_scope_pass=observed['qualified_scope_pass'],
                          units_passed=sum(x['outcome']=='Passed' for x in units.values()),units_total=len(units),
                          resource_limited_units=limited,targets={n:units[n] for n in TARGETS},all_units=units))
    warnings=c.read(c.ROOT/'warning-replay-001.json')
    return dict(status='COMPLETED_SOURCE_BOUND_STABILITY_REVIEW',model_calls=0,native_invocations=4,cases=cases,
                analysis_code_sha256=c.sha(c.ROOT/'analyze.py'),runtime_sha256=c.sha(c.ROOT/'runtime-freeze.json'),
                job_id=c.read(c.ROOT/'submissions/dafny-vmc.json')['job_id'],same_compute_host=c.read(out/'environment.json')['host'],
                unchanged_parent_files=len(parent['files']),transferred_files=len(transfer['files']),
                resource_limited_counts_are_censored=True,original_model_scores_unchanged=True,
                warning_observations=len(warnings['rows']),
                warning_policy_changes=[r['id'] for r in warnings['rows'] if r['eligible_under_policy_v2']!=r['legacy_qualified_scope_pass']])

if __name__=='__main__':
    result=analyze();write(c.ROOT/'analysis-001.json',result)
    print(json.dumps({**{k:v for k,v in result.items() if k!='cases'},
                     'cases':[{k:v for k,v in x.items() if k!='all_units'} for x in result['cases']]},indent=2))
