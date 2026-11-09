"""Reuse only byte-identical core evidence; no verifier or model invocation."""
import json
from pathlib import Path
from preflight import sha,load,save,diagnostic,matches

ROOT=Path(__file__).resolve().parent
PARENT_MANIFEST='f224488c9e3e95c4072e5485d6238d669c6782e1bd8792a4af3b12ec52ef76fe'

def assemble():
    old=ROOT.parent/'verification-001';new=ROOT/'verification-001'
    assert sha((old/'manifest.json').read_bytes())==PARENT_MANIFEST
    assert (new/'manifest.json').read_bytes()==(ROOT/'manifest.json').read_bytes()
    for archive in [old,new]:
        for name,h in load(archive/'manifest.json').items():
            assert sha((archive/name).read_bytes())==h,(archive,name)
        env=load(archive/'environment.json')
        assert env['model_calls']==0 and 'login' not in env['host'] and env['phase']=='core'
        assert env['dafny']=='4.11.0+fcb2042d6d043a2634f0854338c08feeaaaf4ae2'
        assert env['z3']=='Z3 version 4.12.1 - 64 bit'
        # Same staging, actual verifier wrapper and package dependencies.
        for p in (ROOT/'code').rglob('*.py'):
            assert p.read_bytes()==(archive/p.relative_to(ROOT)).read_bytes()
    assert load(old/'summary.json')['completed']==32
    assert load(new/'summary.json')['completed']==8
    checks=[c for c in load(ROOT/'checks.json') if c['phase']=='core']
    rows=[]
    for c in checks:
        reused=not c['task_id'].startswith('map_swap-');archive=old if reused else new
        path=archive/(c['task_id']+'-'+c['variant']+'.json');r=load(path)
        assert r['source_sha256']==c['source_sha256']
        assert {p.name:sha(p.read_bytes()) for p in (archive/c['path']).glob('*.dfy')}==c['source_sha256']
        assert r['matched'] and matches(c,r) and r['diagnostic']==diagnostic(r)
        assert r['model_calls']==0 and r['attempts']==1
        assert r['command']==['timeout','-k','5s','60s','dafny','verify','--verify-included-files','All.dfy']
        rows.append(dict(task_id=c['task_id'],variant=c['variant'],expected=c['expected'],
            source_sha256=c['source_sha256'],reused=reused,evidence=str(path.relative_to(ROOT.parent)),
            evidence_sha256=sha(path.read_bytes()),job_id=load(archive/'environment.json')['job_id']))
    assert len(rows)==32 and sum(r['reused'] for r in rows)==24
    report=dict(phase='combined-core',planned=32,matched=32,all_expected=True,
        new_checks=8,reused_checks=24,new_model_calls=0,
        manifest_sha256=sha((ROOT/'manifest.json').read_bytes()),
        interpretation='24 byte-identical prior observations plus eight new map checks; not 32 new trials',rows=rows)
    save(ROOT/'reference-gate.json',report)
    print(json.dumps({k:v for k,v in report.items() if k!='rows'},indent=2))
    return report

if __name__=='__main__':assemble()
