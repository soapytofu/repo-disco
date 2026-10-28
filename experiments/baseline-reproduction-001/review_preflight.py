"""Review saved preflight inputs, classifications and deterministic selection."""
from collections import Counter
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'preflight-001'
DATA=ROOT.parents[2]/'baseline-inputs/DafnyBench'
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    manifest=load(ROOT/'dataset-manifest.json')
    assert (OUT/'dataset-manifest.json').read_bytes()==(ROOT/'dataset-manifest.json').read_bytes()
    assert sha(OUT/'preflight.py')==sha(ROOT/'preflight.py')
    expected={r['path']:r for r in manifest['files']};reports=[]
    for name,item in expected.items():
        assert sha(DATA/name)==item['sha256'],name
        report=load((OUT/'logs'/name).with_suffix('.json'))
        assert all(report[k]==v for k,v in item.items()),name
        assert report['command']==['timeout','-k','5s','10s','dafny','verify','program.dfy']
        legacy='SUCCESS' if '0 errors' in report['stdout'] else 'GOAL_UNPROVEN' if 'postcondition' in report['stdout'] else 'FAIL'
        assert report['legacy_outcome']==legacy
        reports.append(report)
    assert len(list((OUT/'logs').rglob('*.json')))==len(expected)==1567
    eligible=[r for r in reports if r['partition']=='hints_removed' and r['legacy_outcome']!='SUCCESS']
    ordered=sorted(eligible,key=lambda r:hashlib.sha256(('baseline-reproduction-001:'+r['path']).encode()).hexdigest())
    selection=[{k:r[k] for k in ['path','sha256','exit_code','legacy_outcome']} for r in ordered]
    assert selection==load(OUT/'eligible.json')
    assert selection[:20]==load(OUT/'smoke-selection.json')
    summary=load(OUT/'summary.json');assert summary['eligible_count']==len(eligible)==555
    assert summary['model_calls']==0 and summary['paper_identity_match_confirmed'] is False
    env=load(OUT/'environment.json');assert '4.11.0' in env['versions']['dafny'] and '4.12.1' in env['versions']['z3']
    categories={part:dict(Counter(str(r['exit_code']) for r in reports if r['partition']==part)) for part in manifest['counts']}
    return dict(all_hashes_and_classifications_match=True,total_files=1567,eligible=555,
        paper_count_match=True,paper_identity_confirmed=False,model_calls=0,exit_code_counts=categories,
        strict_legacy_disagreements=[r['path'] for r in reports if (r['exit_code']==0)!=(r['legacy_outcome']=='SUCCESS')],
        nonproof_eligible_count=sum(r['exit_code']!=4 for r in eligible),
        selected_initial_exit_codes=dict(Counter(str(r['exit_code']) for r in selection[:20])),
        selected=selection[:20],environment=env)

if __name__=='__main__':
    report=main();(ROOT/'preflight-review.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='selected'},indent=2))
