"""Five separate analyst candidates, once each on compute; no models or retries."""
import argparse,os,re,shutil,socket,subprocess
from pathlib import Path
import prepare as p
from logging_verifier import verify
import target_metrics
ROOT=Path(__file__).resolve().parent
TOOLCHAIN='4.11.0+fcb2042d6d043a2634f0854338c08feeaaaf4ae2'
Z3='Z3 version 4.12.1 - 64 bit'
COMMAND=['timeout','-k','5s','60s','dafny','verify','--verify-included-files','--log-format','csv','All.dfy']

def classify(evidence,expected):
    code=evidence['exit_code'];text=evidence['stdout']+'\n'+evidence['stderr']
    summaries=re.findall(r'^Dafny program verifier finished with (\d+) verified, (\d+) errors?\s*$',text,re.M)
    clean=len(summaries)==1 and summaries[0]==(str(expected),'0') and ': Error:' not in text
    frontend=bool(re.search(r'(?:parse|resolution/type) errors? detected',text,re.I))
    if code==0:return 'strict_success' if clean and 'warning' not in text.lower() else 'evidence_mismatch'
    if code==4:
        if len(summaries)!=1 or int(summaries[0][1])==0 or ': Error:' not in text or frontend:return 'evidence_mismatch'
        return 'termination_failure' if re.search(r'decreases clause|decreases expression|cannot prove termination',text,re.I) else 'proof_failure'
    if code==2:
        if clean and ': Warning:' in text and '--allow-warnings is false' in text:return 'warning_only'
        return 'frontend_failure' if frontend and ': Error:' in text else 'evidence_mismatch'
    return 'verifier_timeout' if code in (124,137) else 'verifier_stop'

def measured(ev,scope,expected):
    if classify(ev,expected) not in ('strict_success','proof_failure','termination_failure','warning_only'):
        return dict(available=False,reason='No proof-level verification')
    assert ev['command']==COMMAND and ev['attempts']==1 and ev['model_calls']==0
    assert {n:p.digest(t.encode()) for n,t in ev['csv'].items()}==ev['csv_sha256']
    score=target_metrics.scores(ev['csv'],scope,{n:set(k) for n,k in scope['expected_units'].items()})
    assert score['supplied_providers_verified'],'Protected provider failed'
    if classify(ev,expected)=='strict_success':assert all(score['local_targets'].values())
    return dict(available=True,**score)

def live_environment():
    assert os.environ.get('SLURM_JOB_ID','').isdigit() and 'login' not in socket.gethostname().lower(),'Compute node required'
    assert os.environ.get('SLURM_JOB_PARTITION') in ('test','shared','sapphire') and os.environ.get('SLURM_RESTART_COUNT','0')=='0'
    version=subprocess.run(['dafny','--version'],capture_output=True,text=True,check=True,timeout=15).stdout.strip()
    z3=subprocess.run(['z3','--version'],capture_output=True,text=True,check=True,timeout=15).stdout.strip()
    assert version==TOOLCHAIN and z3==Z3
    return dict(job_id=os.environ['SLURM_JOB_ID'],partition=os.environ['SLURM_JOB_PARTITION'],host=socket.gethostname(),
                dafny=version,z3=z3,model_calls=0,offline_fake=False)

def run(root=ROOT,*,verifier=verify,environment=live_environment):
    pins=p.load(root/'manifest.json')
    for name,h in pins.items():assert p.sha(root/name)==h,name
    p.validate_inputs(root)
    generated=p.candidates(root);cases=[c for c,_,_ in generated];assert cases==p.load(root/'cases.json')
    selected=[c for c in cases if c['admitted']]
    out=root/'verification-001';out.mkdir(exist_ok=False)
    for name in [*pins,'manifest.json']:
        dest=out/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(root/name,dest)
    env=environment();p.save(out/'environment.json',env)
    assert env['dafny']==TOOLCHAIN and env['z3']==Z3 and env['model_calls']==0
    scope=p.load(root/'frozen-001/measurement-scope.json');results=[]
    for case in selected:
        source=p.files(root/case['path']);assert p.hashes(source)==case['source_sha256']
        ev=verifier(source);assert ev['source_sha256']==case['source_sha256']
        category=classify(ev,case['expected_verified_obligations'])
        row=dict(case_id=case['case_id'],parent_trial=case['parent_trial'],category=category,**ev)
        try:row['target_metrics']=measured(ev,scope['tasks'][case['task_id']],case['expected_verified_obligations'])
        except (AssertionError,ValueError,KeyError,TypeError) as error:
            row['target_metrics']=dict(available=False,error_type=type(error).__name__);row['measurement_failed']=True
        row['matched']=category=='strict_success' and not row.get('measurement_failed',False)
        p.save(out/(case['case_id']+'.json'),row);results.append(row)
        for name,text in ev['csv'].items():
            path=Path(name);assert not path.is_absolute() and '..' not in path.parts
            dest=out/'raw-csv'/case['case_id']/path;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(text.encode())
        p.save(out/'summary.json',dict(planned=len(selected),cases=5,completed=len(results),model_calls=0,
            all_expected=len(results)==len(selected) and all(r['matched'] for r in results),results=results,
            claim='Analyst edit sufficiency hypotheses; original model score remains27/32'))
        print(case['case_id'],category,'exit',ev['exit_code'],flush=True)
        if category in ('evidence_mismatch','verifier_timeout','verifier_stop','frontend_failure') or row.get('measurement_failed'):
            raise RuntimeError('Unexpected verifier evidence; preserve output, no retries')
    return len(selected)==5 and all(r['matched'] for r in results)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',choices=['verification-001'],required=True);parser.parse_args()
    if not run():raise SystemExit('Analyst hypothesis failed; evidence retained, no automatic repair')

if __name__=='__main__':main()
