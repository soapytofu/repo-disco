"""No-model data/version/eligibility audit. Real verification is compute-only."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parent

def validate_dataset(data,manifest):
    if subprocess.check_output(['git','-C',str(data),'rev-parse','HEAD'],text=True).strip()!=manifest['revision']:
        raise ValueError('Dataset revision mismatch')
    expected={item['path']:item['sha256'] for item in manifest['files']}
    actual={str(p.relative_to(data)):hashlib.sha256(p.read_bytes()).hexdigest() for part in ['ground_truth','hints_removed'] for p in (data/'DafnyBench/dataset'/part).rglob('*.dfy')}
    if actual!=expected:raise ValueError('Dataset file set or bytes differ')

def verify(item,data,out):
    content=(data/item['path']).read_bytes()
    command=['timeout','-k','5s','10s','dafny','verify','program.dfy']
    with tempfile.TemporaryDirectory(prefix='baseline-preflight-') as temp:
        (Path(temp)/'program.dfy').write_bytes(content)
        proc=subprocess.run(command,cwd=temp,capture_output=True,text=True)
    # Match the pinned backend's outcome heuristic, retaining stricter diagnostics separately.
    legacy='SUCCESS' if '0 errors' in proc.stdout else 'GOAL_UNPROVEN' if 'postcondition' in proc.stdout else 'FAIL'
    report=dict(**item,exit_code=proc.returncode,legacy_outcome=legacy,stdout=proc.stdout,stderr=proc.stderr,command=command)
    dest=out/'logs'/item['path'];dest.parent.mkdir(parents=True,exist_ok=True)
    dest.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n')
    return report

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--dataset',type=Path,required=True);ap.add_argument('--output',type=Path);ap.add_argument('--audit-only',action='store_true');args=ap.parse_args()
    manifest=json.loads((ROOT/'dataset-manifest.json').read_text());validate_dataset(args.dataset,manifest)
    if args.audit_only:print(json.dumps(dict(hashes_match=True,counts=manifest['counts'],model_calls=0)));return
    if not os.environ.get('SLURM_JOB_ID') or 'login' in socket.gethostname():raise SystemExit('Requires Slurm compute node')
    if args.output is None:raise SystemExit('--output required')
    out=args.output;out.mkdir(parents=True,exist_ok=False)
    for name in ['dataset-manifest.json','run-plan.json','preflight.py']:shutil.copy2(ROOT/name,out/name)
    versions={name:subprocess.run([name,'--version'],capture_output=True,text=True,check=True).stdout.strip() for name in ['dafny','z3']}
    (out/'environment.json').write_text(json.dumps(dict(versions=versions,host=socket.gethostname(),job=os.environ['SLURM_JOB_ID'],model_calls=0),indent=2)+'\n')
    if '4.11.0' not in versions['dafny'] or '4.12.1' not in versions['z3']:raise SystemExit('Verifier version differs from proposed pin; review before proceeding')
    with ThreadPoolExecutor(max_workers=4) as pool:reports=list(pool.map(lambda item:verify(item,args.dataset,out),manifest['files']))
    eligible=[r for r in reports if r['partition']=='hints_removed' and r['legacy_outcome']!='SUCCESS']
    ordered=sorted(eligible,key=lambda r:hashlib.sha256(('baseline-reproduction-001:'+r['path']).encode()).hexdigest())
    selection=[{k:r[k] for k in ['path','sha256','exit_code','legacy_outcome']} for r in ordered]
    (out/'eligible.json').write_text(json.dumps(selection,indent=2)+'\n')
    (out/'smoke-selection.json').write_text(json.dumps(selection[:20],indent=2)+'\n')
    summary=dict(model_calls=0,total_files=len(reports),eligible_count=len(eligible),paper_count=555,count_matches_paper=len(eligible)==555,maximum_full_calls=4*len(eligible),nonproof_eligible=[r['path'] for r in eligible if r['exit_code']!=4],paper_identity_match_confirmed=False,live_run_allowed=False)
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
