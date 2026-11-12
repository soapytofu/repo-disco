"""Compute-only, single-pass collection of declaration-level verifier logs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import time

ROOT=Path(__file__).resolve().parent


def sha(raw):return hashlib.sha256(raw).hexdigest()
def load(path):return json.loads(path.read_text())
def save(path,value):path.write_text(json.dumps(value,indent=2)+'\n')


def verify(files):
    assert set(files)=={'Kernel.dfy','Api.dfy','Ops1.dfy','Ops2.dfy','HelperA.dfy','HelperB.dfy','ClientA.dfy','ClientB.dfy','All.dfy'}
    assert all(isinstance(b,bytes) for b in files.values())
    command=['timeout','-k','5s','60s','dafny','verify','--verify-included-files','--log-format','csv','All.dfy']
    started=time.monotonic()
    with tempfile.TemporaryDirectory(prefix='repodisco-targets-') as directory:
        folder=Path(directory)
        for name,raw in files.items():(folder/name).write_bytes(raw)
        p=subprocess.run(command,cwd=folder,capture_output=True,text=True)
        csv_files={str(path.relative_to(folder)):path.read_text() for path in sorted(folder.rglob('*.csv'))}
    return dict(command=command,exit_code=p.returncode,stdout=p.stdout,stderr=p.stderr,
                elapsed_seconds=time.monotonic()-started,source_sha256={n:sha(b) for n,b in files.items()},
                csv=csv_files,csv_sha256={n:sha(s.encode()) for n,s in csv_files.items()},model_calls=0,attempts=1)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--phase',choices=['core'],required=True)
    parser.add_argument('--output',required=True);a=parser.parse_args()
    if not os.environ.get('SLURM_JOB_ID') or 'login' in socket.gethostname():raise SystemExit('Compute node required')
    assert a.output=='verification-001'
    manifest=load(ROOT/'manifest.json')
    for name,h in manifest.items():assert sha((ROOT/name).read_bytes())==h,name
    out=ROOT/a.output;out.mkdir(exist_ok=False)
    for name in [*manifest,'manifest.json']:
        dest=out/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,dest)
    version=subprocess.run(['dafny','--version'],capture_output=True,text=True,check=True,timeout=15).stdout.strip()
    z3=subprocess.run(['z3','--version'],capture_output=True,text=True,check=True,timeout=15).stdout.strip()
    assert version=='4.11.0+fcb2042d6d043a2634f0854338c08feeaaaf4ae2'
    assert z3=='Z3 version 4.12.1 - 64 bit'
    save(out/'environment.json',dict(job_id=os.environ['SLURM_JOB_ID'],host=socket.gethostname(),
        partition=os.environ.get('SLURM_JOB_PARTITION'),dafny=version,z3=z3,model_calls=0))
    cases=load(ROOT/'cases.json');assert len(cases)==4;rows=[]
    for case in cases:
        files={p.name:p.read_bytes() for p in (ROOT/case['path']).glob('*.dfy')}
        assert {n:sha(b) for n,b in files.items()}==case['source_sha256']
        result=verify(files)
        matched=result['exit_code']==case['expected_exit'] and bool(result['csv'])
        row=dict(case_id=case['case_id'],expected_exit=case['expected_exit'],matched=matched,**result)
        rows.append(row);save(out/(case['case_id']+'.json'),row)
        for name,text in result['csv'].items():
            dest=out/'raw-csv'/case['case_id']/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(text)
        save(out/'summary.json',dict(model_calls=0,planned=4,completed=len(rows),all_expected=all(x['matched'] for x in rows),
            phase='core',results=rows,claim='Exit/logger check only; named-target review follows offline'))
        print(case['case_id'],result['exit_code'],'csv_files',len(result['csv']),flush=True)
        if result['exit_code'] not in (0,4) or not result['csv']:
            raise SystemExit('Unexpected verifier/logger result; no retry')
    if not all(x['matched'] for x in rows):raise SystemExit(1)


if __name__=='__main__':main()
