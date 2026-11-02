"""Audit all 164 final fixture outcomes without running a verifier or model."""
from collections import Counter,defaultdict
from pathlib import Path
import json
from preflight import load,save,sha,matches,diagnostic

ROOT=Path(__file__).resolve().parent
EXPERIMENT=ROOT.parent


def main():
    checks=load(ROOT/'checks.json'); tasks={t['task_id']:t for t in load(ROOT/'tasks.json')}
    gate=load(ROOT/'reference-gate.json')
    assert gate['gate']=='passed'
    assert gate['review_script_sha256']==sha((ROOT/'review_reference_gate.py').read_bytes())
    assert gate['current_manifest_sha256']==sha((ROOT/'manifest.json').read_bytes())
    ref={(r['task_id'],r['variant']):r for r in gate['rows']}
    assert len(ref)==len(gate['rows'])==48
    negative=ROOT/'verification-002'; summary=load(negative/'summary.json')
    assert summary['planned']==summary['completed']==len(summary['results'])==116
    assert summary['all_expected']
    sub=load(ROOT/'submission-negatives.json')
    assert sub['reference_gate_sha256']==sha((ROOT/'reference-gate.json').read_bytes())
    rows=[];identities=set();families=defaultdict(Counter);categories=Counter()
    for check in checks:
        identity=(check['task_id'],check['variant'])
        assert identity not in identities;identities.add(identity)
        if identity in ref:
            link=ref[identity];path=EXPERIMENT/link['evidence'];reused=link['reused_identical_prior_result']
            assert sha(path.read_bytes())==link['evidence_sha256']
        else:
            path=negative/(check['task_id']+'-'+check['variant']+'.json');reused=False
        row=load(path);archive=path.parent
        assert (row['task_id'],row['variant'])==identity
        assert row['expected']==check['expected'] and row['matched'] and matches(check,row)
        assert row['diagnostic']==diagnostic(row)==check['expected']
        assert row['model_calls']==0 and row['attempts']==1
        assert '--verify-included-files' in row['command']
        assert 'parse error' not in (row['stdout']+row['stderr']).lower()
        current={p.name:sha(p.read_bytes()) for p in (ROOT/check['path']).glob('*.dfy')}
        archived={p.name:sha(p.read_bytes()) for p in (archive/check['path']).glob('*.dfy')}
        assert current==archived==check['source_sha256']==row['source_sha256']
        manifest=load(archive/'manifest.json')
        for name,h in archived.items():assert manifest[check['path']+'/'+name]==h
        env=load(archive/'environment.json');family=tasks[check['task_id']]['family']
        families[family][row['diagnostic']]+=1;categories[row['diagnostic']]+=1
        rows.append(dict(task_id=check['task_id'],variant=check['variant'],family=family,
            expected=check['expected'],diagnostic=row['diagnostic'],exit_code=row['exit_code'],
            job_id=env['job_id'],source_sha256=current,evidence=str(path.relative_to(EXPERIMENT)),
            evidence_sha256=sha(path.read_bytes()),reused_identical_prior_result=reused))
    assert len(rows)==164
    assert categories==dict(success=24,proof_failure=120,termination_failure=8,resolution_failure=12)
    assert sum(r['reused_identical_prior_result'] for r in rows)==44
    actual=load(EXPERIMENT/'runtime-002/verification-001/summary.json')['completed']
    actual+=load(ROOT/'verification-001/summary.json')['completed']+summary['completed']
    assert actual==168
    report=dict(status='all_expected',final_fixture_conditions=164,all_expected=True,
        source_revision='revision-003',categories=categories,by_family=dict(families),
        actual_dafny_invocations_across_history=168,preserved_failed_original_references=4,
        reused_identical_outcomes=44,reuse_is_not_new_trials=True,new_model_calls=0,
        no_parse_failures_in_final_set=True,current_manifest_sha256=sha((ROOT/'manifest.json').read_bytes()),
        review_script_sha256=sha(Path(__file__).read_bytes()),rows=rows)
    save(ROOT/'completion-review.json',report)
    print(json.dumps({k:v for k,v in report.items() if k!='rows'},indent=2))


if __name__=='__main__':main()
