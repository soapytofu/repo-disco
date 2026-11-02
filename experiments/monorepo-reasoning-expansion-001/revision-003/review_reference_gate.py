"""Combine 44 byte-identical prior outcomes with four revised reference checks.

Offline audit only: every selected result must match this revision's exact nine
source files. Reuse never creates additional trials or replaces prior failures.
"""
import json
from pathlib import Path
from preflight import sha,load,save,matches

ROOT=Path(__file__).resolve().parent
EXPERIMENT=ROOT.parent


def main():
    checks=[c for c in load(ROOT/'checks.json') if c['variant'] in ('reference','empty')]
    rows=[];seen=set()
    for check in checks:
        identity=(check['task_id'],check['variant'])
        assert identity not in seen;seen.add(identity)
        corrected=check['task_id'].startswith('reverse_concat-') and check['variant']=='reference'
        run=ROOT if corrected else EXPERIMENT/'runtime-002'
        out=run/'verification-001'
        manifest=load(out/'manifest.json')
        assert manifest==load(run/'manifest.json')
        record_path=out/(check['task_id']+'-'+check['variant']+'.json')
        row=load(record_path)
        assert (row['task_id'],row['variant'])==identity
        assert row['expected']==check['expected'] and row['matched'] and matches(check,row)
        assert row['attempts']==1 and row['model_calls']==0
        current={p.name:sha(p.read_bytes()) for p in (ROOT/check['path']).glob('*.dfy')}
        archived={p.name:sha(p.read_bytes()) for p in (out/check['path']).glob('*.dfy')}
        assert current==archived==check['source_sha256']==row['source_sha256']
        for name,h in archived.items():assert manifest[check['path']+'/'+name]==h
        environment=load(out/'environment.json')
        rows.append(dict(task_id=check['task_id'],variant=check['variant'],expected=check['expected'],
            exit_code=row['exit_code'],diagnostic=row['diagnostic'],source_sha256=current,
            job_id=environment['job_id'],reused_identical_prior_result=not corrected,
            evidence=str(record_path.relative_to(EXPERIMENT)),evidence_sha256=sha(record_path.read_bytes()),
            archived_manifest_sha256=sha((out/'manifest.json').read_bytes())))
    assert len(rows)==48
    assert sum(r['expected']=='success' for r in rows)==24
    assert sum(r['reused_identical_prior_result'] for r in rows)==44
    report=dict(gate='passed',reference_successes=24,empty_proof_failures=24,
        new_checks=4,reused_identical_checks=44,new_model_calls=0,
        reuse_is_not_new_independent_trials=True,
        review_script_sha256=sha(Path(__file__).read_bytes()),
        current_manifest_sha256=sha((ROOT/'manifest.json').read_bytes()),rows=rows)
    save(ROOT/'reference-gate.json',report)
    print(json.dumps({k:v for k,v in report.items() if k!='rows'},indent=2))


if __name__=='__main__':main()
