"""One compute-only verification per admitted saved candidate; no models or retries."""
import argparse,json,os,re,shutil,socket,subprocess,time
from pathlib import Path
import prepare as p
from logging_verifier import verify
import target_metrics
ROOT=Path(__file__).resolve().parent
TOOLCHAIN='4.11.0+fcb2042d6d043a2634f0854338c08feeaaaf4ae2'
Z3='Z3 version 4.12.1 - 64 bit'
COMMAND=['timeout','-k','5s','60s','dafny','verify','--verify-included-files','--log-format','csv','All.dfy']

def classify(ev):
    text=ev['stdout']+'\n'+ev['stderr'];code=ev['exit_code']
    summaries=re.findall(r'^Dafny program verifier finished with (\d+) verified, (\d+) errors?\s*$',text,re.M)
    clean=len(summaries)==1 and summaries[0]==('11','0') and ': Error:' not in text
    if code==0:return 'strict_success' if clean and 'warning' not in text.lower() else 'evidence_mismatch'
    if code==4:
        if re.search(r'parse errors?|resolution/type errors?',text,re.I):return 'unexpected_frontend_exit'
        return 'termination_failure' if re.search(r'decreases clause|decreases expression|cannot prove termination',text,re.I) else 'proof_failure'
    if code==2:return 'warning_only' if clean and ': Warning:' in text else 'frontend_failure'
    if code in (124,137):return 'verifier_timeout'
    return 'verifier_stop'

def measured(ev,scope):
    if classify(ev) not in ('strict_success','proof_failure','termination_failure','warning_only'):
        return dict(available=False,reason='No proof-level result')
    assert ev['csv'], 'Missing declaration log'
    assert {n:p.digest(t.encode()) for n,t in ev['csv'].items()}==ev['csv_sha256']
    score=target_metrics.scores(ev['csv'],scope,{n:set(k) for n,k in scope['expected_units'].items()})
    if classify(ev)=='strict_success':assert score['supplied_providers_verified'] and all(score['local_targets'].values())
    return dict(available=True,**score)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',choices=['verification-001'],required=True);a=parser.parse_args()
    if not os.environ.get('SLURM_JOB_ID') or 'login' in socket.gethostname():raise SystemExit('Compute allocation required')
    pins=p.load(ROOT/'manifest.json')
    for n,h in pins.items():assert p.sha(ROOT/n)==h,n
    p.validate_inputs(ROOT)
    out=ROOT/a.output;out.mkdir(exist_ok=False)
    for n in [*pins,'manifest.json']:
        dest=out/n;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/n,dest)
    version=subprocess.run(['dafny','--version'],capture_output=True,text=True,check=True,timeout=15).stdout.strip()
    z3=subprocess.run(['z3','--version'],capture_output=True,text=True,check=True,timeout=15).stdout.strip()
    p.save(out/'environment.json',dict(job_id=os.environ['SLURM_JOB_ID'],partition=os.environ.get('SLURM_JOB_PARTITION'),host=socket.gethostname(),dafny=version,z3=z3,model_calls=0))
    assert version==TOOLCHAIN and z3==Z3
    cases=p.load(ROOT/'cases.json');assert len(cases)==8
    scope=p.load(ROOT/'frozen-001/measurement-scope.json');assert scope['interpreter_sha256']==p.sha(ROOT/'target_metrics.py')
    selected=[c for c in cases if c['admitted']];results=[]
    for c in selected:
        fs=p.files(ROOT/c['path']);assert p.hashes(fs)==c['source_sha256']
        ev=verify(fs);category=classify(ev)
        row=dict(case_id=c['case_id'],parent_trial=c['parent_trial'],expected_diagnostic=c['expected_diagnostic'],category=category,**ev)
        try:row['target_metrics']=measured(ev,scope['tasks'][c['task_id']])
        except (ValueError,KeyError,AssertionError,TypeError) as error:
            row['target_metrics']=dict(available=False,error_type=type(error).__name__,reason=str(error));row['measurement_failed']=True
        results.append(row);p.save(out/(c['case_id']+'.json'),row)
        for name,text in ev['csv'].items():
            path=Path(name);assert not path.is_absolute() and '..' not in path.parts
            dest=out/'raw-csv'/c['case_id']/path;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(text.encode())
        p.save(out/'summary.json',dict(model_calls=0,planned=len(selected),saved_responses=8,completed=len(results),
            all_strict_verified=all(x['category']=='strict_success' and not x.get('measurement_failed') for x in results),results=results,
            claim='Retrospective exact-fence diagnostic, never primary model rescoring'))
        print(c['case_id'],category,'exit',ev['exit_code'],flush=True)
        if category in ('verifier_timeout','verifier_stop','evidence_mismatch','unexpected_frontend_exit') or row.get('measurement_failed'):
            raise SystemExit('Unexpected verifier/measurement condition; preserve output, no retries')
    if any(x['category']!='strict_success' for x in results):raise SystemExit(1)

if __name__=='__main__':main()
