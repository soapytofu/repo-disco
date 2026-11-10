"""Exactly one compute-only pass through a selected set of trusted fixtures."""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import socket
import subprocess
import sys

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'code'))
from language.dafny.repository import verify_repository


def sha(data): return hashlib.sha256(data).hexdigest()
def load(path): return json.loads(path.read_text())
def save(path,data): path.write_text(json.dumps(data,indent=2)+'\n')


def diagnostic(row):
    text=(row['stdout']+'\n'+row['stderr']).lower()
    if row['exit_code']==0:
        summaries=re.findall(r'dafny program verifier finished with (\d+) verified, (\d+) errors?',text)
        return 'success' if len(summaries)==1 and int(summaries[0][1])==0 and 'warning' not in text and ': error:' not in text else 'unexpected_diagnostic'
    if 'parse errors' in text or 'syntax error' in text:return 'parse_error'
    if row['exit_code']==4:
        if 'decreases' in text or 'termination' in text:return 'termination_failure'
        if any(s in text for s in ['postcondition','precondition','assertion','for this call','ensures']):return 'proof_failure'
    if row['exit_code']==2 and any(s in text for s in ['does not exist','unresolved','not found','not a member']):
        return 'resolution_failure'
    return 'unexpected_diagnostic'


def matches(check,row): return check['expected']==diagnostic(row)


def selected(checks,phase):
    if phase!='all': raise ValueError('Only the fixed complete control set')
    return checks


def main():
    p=argparse.ArgumentParser();p.add_argument('--phase',choices=['all'],required=True)
    p.add_argument('--output',required=True);args=p.parse_args()
    if not os.environ.get('SLURM_JOB_ID') or 'login' in socket.gethostname():
        raise SystemExit('Slurm compute node required')
    if '/' in args.output or not args.output.startswith('verification-'): raise ValueError('Fresh local output name required')
    manifest=load(ROOT/'manifest.json')
    for name,h in manifest.items():
        if sha((ROOT/name).read_bytes())!=h:raise ValueError('Input drift: '+name)
    out=ROOT/args.output;out.mkdir(exist_ok=False)
    for name in [*manifest,'manifest.json']:
        dest=out/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,dest)
    save(out/'environment.json',dict(job_id=os.environ['SLURM_JOB_ID'],host=socket.gethostname(),
        partition=os.environ.get('SLURM_JOB_PARTITION'),python=sys.version,model_calls=0,phase=args.phase,
        dafny=subprocess.run(['dafny','--version'],capture_output=True,text=True,check=True,timeout=15).stdout.strip(),
        z3=subprocess.run(['z3','--version'],capture_output=True,text=True,check=True,timeout=15).stdout.strip()))
    env=load(out/'environment.json')
    if env['dafny']!='4.11.0+fcb2042d6d043a2634f0854338c08feeaaaf4ae2':raise ValueError('Dafny version drift')
    if env['z3']!='Z3 version 4.12.1 - 64 bit':raise ValueError('Z3 version drift')
    checks=selected(load(ROOT/'checks.json'),args.phase);rows=[]
    if len(checks)!=6:raise ValueError('Expected fixed 6 controls')
    save(out/'selected-checks.json',checks)
    for check in checks:
        files={p.name:p.read_bytes() for p in (ROOT/check['path']).glob('*.dfy')}
        if {n:sha(b) for n,b in files.items()}!=check['source_sha256']:raise ValueError('Source drift')
        v=verify_repository(files,'All.dfy',timeout=60).evidence
        row=dict(task_id=check['task_id'],variant=check['variant'],expected=check['expected'],
                 diagnostic=diagnostic(v),matched=matches(check,v),**v);rows.append(row)
        save(out/(check['task_id']+'-'+check['variant']+'.json'),row)
        save(out/'summary.json',dict(model_calls=0,phase=args.phase,planned=len(checks),completed=len(rows),
            all_expected=all(r['matched'] for r in rows),results=rows))
        print(check['task_id'],check['variant'],v['exit_code'],row['diagnostic'],row['matched'],flush=True)
        if v['exit_code'] not in (0,2,4):raise SystemExit('Infrastructure failure; no retries')
    if not all(r['matched'] for r in rows):raise SystemExit(1)


if __name__=='__main__':main()
