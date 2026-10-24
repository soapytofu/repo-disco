"""Compute-only replay of post-hoc extracted responses; no model calls."""
import argparse,json,os,shutil,socket,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'evaluator'))
from harness import evaluate

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    if not os.environ.get('SLURM_JOB_ID') or 'login' in socket.gethostname():raise SystemExit('Compute node required')
    out=args.output;out.mkdir(parents=True,exist_ok=False)
    snap=out/'snapshot';snap.mkdir()
    for name in ['verify.py','extract.py','extraction.json']:shutil.copy2(ROOT/name,snap/name)
    for name in ['evaluator','extracted']:shutil.copytree(ROOT/name,snap/name,ignore=shutil.ignore_patterns('__pycache__'))
    rows=[]
    for item in json.loads((ROOT/'extraction.json').read_text()):
        folder=out/item['directory'];raw=(ROOT/'extracted'/item['directory']/'response.json').read_text()
        result=evaluate(item['condition'],raw,folder)
        rows.append(dict(sequence=item['sequence'],condition=item['condition'],directory=item['directory'],result=result))
        (out/'results.json').write_text(json.dumps(rows,indent=2)+'\n')
        print(item['sequence'],item['condition'],result['outcome'],flush=True)
        if result['outcome'] in ['TIMEOUT','VERIFIER_ERROR']:break
    (out/'environment.json').write_text(json.dumps(dict(job_id=os.environ['SLURM_JOB_ID'],host=socket.gethostname(),dafny=subprocess.check_output(['dafny','--version'],text=True).strip(),z3=subprocess.check_output(['z3','--version'],text=True).strip(),model_calls=0),indent=2)+'\n')
    (out/'summary.json').write_text(json.dumps(dict(responses=len(rows),successes=sum(r['result']['outcome']=='SUCCESS' for r in rows),verifier_checks=sum(len(r['result'].get('verification',[])) for r in rows),model_calls=0,post_hoc_diagnostic=True),indent=2)+'\n')
if __name__=='__main__':main()
