"""Replay authored references and empty proofs; zero model calls."""
import argparse,json,os,shutil,socket,subprocess
from pathlib import Path
from harness import ROOT,CLIENTS,evaluate

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    if not os.environ.get('SLURM_JOB_ID') or 'login' in socket.gethostname():raise SystemExit('Compute node required')
    out=args.output;out.mkdir(parents=True,exist_ok=False)
    snapshot=out/'snapshot';snapshot.mkdir()
    for name in ['harness.py','preflight.py','plan.json','protocol.json']:
        shutil.copy2(ROOT/name,snapshot/name)
    for name in ['fixtures','prompts']:shutil.copytree(ROOT/name,snapshot/name)
    results=[]
    for condition in ['shared','separate']:
        for kind in ['reference','missing']:
            raw=json.dumps({name:(ROOT/'fixtures'/f'{condition}_{kind}'/name).read_text() for name in CLIENTS})
            result=evaluate(condition,raw,out/f'{condition}_{kind}')
            expected='SUCCESS' if kind=='reference' else 'PROOF_FAILURE'
            matched=len(result['verification'])==3 and all(r['outcome']==expected for r in result['verification'])
            results.append(dict(condition=condition,input_kind=kind,expected=expected,matches_expectation=matched,result=result))
            (out/'results.json').write_text(json.dumps(results,indent=2)+'\n')
            print(condition,kind,result['outcome'],matched,flush=True)
    env={'job_id':os.environ['SLURM_JOB_ID'],'host':socket.gethostname(),'model_calls':0}
    for tool in ['dafny','z3']:env[tool]=subprocess.check_output([tool,'--version'],text=True).strip()
    (out/'environment.json').write_text(json.dumps(env,indent=2)+'\n')
    good=all(r['matches_expectation'] for r in results)
    (out/'summary.json').write_text(json.dumps(dict(all_expected=good,replays=4,verifier_checks=sum(len(r['result']['verification']) for r in results),model_calls=0),indent=2)+'\n')
    raise SystemExit(0 if good else 1)
if __name__=='__main__':main()
