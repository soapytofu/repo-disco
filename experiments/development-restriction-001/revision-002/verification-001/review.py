"""Offline byte and outcome audit. It never calls Dafny or a model."""
import argparse
import json
from pathlib import Path
from preflight import sha,load,save,matches,diagnostic,selected

ROOT=Path(__file__).resolve().parent


def review(out):
    manifest=load(out/'manifest.json')
    assert manifest==load(ROOT/'manifest.json'), 'Archived input freeze differs'
    for name,h in manifest.items():
        assert sha((out/name).read_bytes())==h,name
    env=load(out/'environment.json');checks=load(out/'selected-checks.json')
    assert checks==selected(load(out/'checks.json'),env['phase'])
    summary=load(out/'summary.json');rows=[]
    assert summary['phase']==env['phase'] and summary['model_calls']==0
    assert summary['completed']==len(summary['results'])==len(checks)==summary['planned']
    for check,record in zip(checks,summary['results']):
        row=load(out/(check['task_id']+'-'+check['variant']+'.json'))
        assert row==record
        assert (row['task_id'],row['variant'])==(check['task_id'],check['variant'])
        files={p.name:sha(p.read_bytes()) for p in (out/check['path']).glob('*.dfy')}
        assert files==check['source_sha256']==row['source_sha256']
        assert row['attempts']==1 and row['model_calls']==0
        assert '--verify-included-files' in row['command']
        assert row['matched']==matches(check,row)
        assert row['diagnostic']==diagnostic(row)
        rows.append({k:row[k] for k in ['task_id','variant','expected','diagnostic','exit_code','matched']})
    assert env['model_calls']==0 and 'login' not in env['host']
    assert summary['all_expected']==all(r['matched'] for r in rows)
    report=dict(job_id=env['job_id'],phase=env['phase'],planned=len(checks),
        matched=sum(r['matched'] for r in rows),all_expected=all(r['matched'] for r in rows),
        new_model_calls=0,manifest_sha256=sha((out/'manifest.json').read_bytes()),
        summary_sha256=sha((out/'summary.json').read_bytes()),rows=rows)
    save(ROOT/(out.name+'-review.json'),report)
    save(ROOT/(out.name+'-sha256.json'),{str(p.relative_to(out)):sha(p.read_bytes()) for p in sorted(out.rglob('*')) if p.is_file()})
    print(json.dumps({k:v for k,v in report.items() if k!='rows'},indent=2))
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output');a=p.parse_args();review(ROOT/a.output)
