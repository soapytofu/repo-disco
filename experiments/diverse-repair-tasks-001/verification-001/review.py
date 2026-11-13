"""Replay fixture generation and classify exact compute evidence; no verifier calls."""
from pathlib import Path
import hashlib,json,re,csv,io
import build as b
ROOT=Path(__file__).resolve().parent
load=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def review():
    out=ROOT/'verification-001';pins=load(ROOT/'manifest.json');assert pins==load(out/'manifest.json')
    for n,h in pins.items():assert sha(ROOT/n)==sha(out/n)==h,n
    env=load(out/'environment.json');assert env['model_calls']==0 and 'login' not in env['host']
    assert env['dafny']=='4.11.0+fcb2042d6d043a2634f0854338c08feeaaaf4ae2'
    assert env['z3']=='Z3 version 4.12.1 - 64 bit'
    cases=load(out/'cases.json');summary=load(out/'summary.json');assert summary['completed']==len(cases)==36
    rows=[]
    for case,ev in zip(cases,summary['results']):
        assert ev==load(out/(case['case_id']+'.json'))
        task=next(t for t in load(ROOT/'tasks.json') if t['task_id']==case['task_id'])
        d=b.DEFINITIONS[task['semantic_instance']]
        generated=b.workspace(task['semantic_instance'],task['sharing'],'\n' if case['variant']=='empty' else d[case['variant']])
        files={p.name:p.read_text() for p in (out/case['path']).glob('*.dfy')}
        assert files==generated and b.hashes(files)==ev['source_sha256']==case['source_sha256']
        assert ev['model_calls']==0 and ev['attempts']==1 and ev['command']==['timeout','-k','5s','60s','dafny','verify','--verify-included-files','--log-format','csv','All.dfy']
        for n,s in ev['csv'].items():
            assert hashlib.sha256(s.encode()).hexdigest()==ev['csv_sha256'][n]
            assert (out/'raw-csv'/case['case_id']/n).read_bytes()==s.encode()
        text=ev['stdout']+'\n'+ev['stderr'];warning='warning' in text.lower()
        errors=re.findall(r'^(\w+\.dfy)\(\d+,\d+\): Error: (.+)$',text,re.M)
        counts=re.findall(r'^Dafny program verifier finished with (\d+) verified, (\d+) errors?\s*$',text,re.M)
        if ev['exit_code']==0 and len(counts)==1 and int(counts[0][0])>0 and counts[0][1]=='0' and not errors and not warning:kind='success'
        elif ev['exit_code']==4 and len(counts)==1 and int(counts[0][1])>0 and errors and not warning:
            kind='termination' if any('decreases' in message or 'decrease' in message for _,message in errors) else 'proof_failure'
        else:kind='frontend_warning_timeout_or_infrastructure'
        primary=case['primary_diagnostic'];specific=True if not primary else any(primary in message for _,message in errors)
        matched=kind==case['expected'] and bool(ev['csv']) and specific
        rows.append(dict(case_id=case['case_id'],task_id=case['task_id'],variant=case['variant'],expected=case['expected'],actual=kind,
            matched=matched,primary_diagnostic_matched=specific,errors=errors,summary=counts,warnings=warning,exit_code=ev['exit_code'],
            source_sha256=ev['source_sha256'],evidence_sha256=sha(out/(case['case_id']+'.json'))))
    report=dict(job_id=env['job_id'],model_calls=0,all_expected=all(r['matched'] for r in rows),checks=rows,
        reference_passes=sum(r['actual']=='success' and r['variant']=='reference' for r in rows),
        alternative_passes=sum(r['actual']=='success' and r['variant']=='alternative' for r in rows),
        primary_failures_validated=sum(r['matched'] and r['variant']=='faulty' for r in rows),reviewer_sha256=sha(Path(__file__)))
    b.save(ROOT/'results-review.json',report)
    b.save(ROOT/'verification-001-sha256.json',{str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file()})
    print(json.dumps({k:v for k,v in report.items() if k!='checks'},indent=2))
    print(json.dumps([r for r in rows if not r['matched']],indent=2))
    if not report['all_expected']:raise SystemExit('Unexpected evidence preserved; deliberate revision required before freeze')

if __name__=='__main__':review()
