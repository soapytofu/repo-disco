"""Compute-only, one attempt per declared native command; zero model calls."""
import base64
import datetime
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import dafny_gate as gate

ROOT=Path(__file__).resolve().parent

def write(path, value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x') as handle: json.dump(value,handle,indent=2,sort_keys=True);handle.write('\n')

def check_pins():
    for manifest in ['runtime-manifest.json','fixture-manifest.json']:
        for name,digest in json.loads((ROOT/manifest).read_bytes()).items():
            gate.require(gate.safe_name(name) and gate.sha((ROOT/name).read_bytes())==digest,'Frozen bundle changed: '+name)

def direct(files, profile, run_id, entry_only=False):
    """Independent staging and subprocess path, without calling the adapter.

    Its source list is independently constructed from staged files. Record encoding
    is shared; native exit, stdout, stderr and CSV are also retained without scoring.
    This compares integration, not two independent theorem provers.
    """
    with tempfile.TemporaryDirectory(prefix='repodisco-direct-') as temporary:
        root=Path(temporary)
        for name,raw in files.items():
            target=root/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
        staged={p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*.dfy')}
        assert staged==files
        source_args=['All.dfy'] if entry_only else sorted(staged)
        command=['dafny','verify','--verify-included-files','--log-format','csv']+source_args
        invocation=['/usr/bin/time','-f','%M','-o','maxrss.txt','timeout','-k','5s','60s']+command
        start=time.monotonic();timed_out=False;error=None
        try:
            p=subprocess.run(invocation,cwd=root,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=75)
            code,out,err=p.returncode,p.stdout,p.stderr
        except subprocess.TimeoutExpired as exc:
            code,out,err=None,exc.stdout or b'',exc.stderr or b'';timed_out=True
        except OSError as exc:
            code,out,err=None,b'',str(exc).encode();error=type(exc).__name__
        elapsed=time.monotonic()-start
        memory=(root/'maxrss.txt').read_text().strip().splitlines() if (root/'maxrss.txt').exists() else []
        peak=int(memory[-1]) if memory and memory[-1].isdigit() else None
        csv_files={p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*.csv')}
        record=gate.record_from_raw(profile,run_id,code,out,err,csv_files,elapsed,peak,timed_out,error)
        record['command']=command
        return record

def archive(output, name, files, profile, record):
    target=output/name;target.mkdir()
    write(target/'record.json',record);write(target/'profile.json',profile)
    for source,raw in files.items():
        path=target/'source'/source;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    for name,encoded in record['raw_base64'].items():
        path=target/'raw'/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(base64.b64decode(encoded,validate=True))

def main():
    assert len(sys.argv)==2 and sys.argv[1]=='verification-001'
    assert os.environ.get('SLURM_JOB_ID') and 'login' not in socket.gethostname().lower()
    check_pins();output=ROOT/sys.argv[1];output.mkdir(exist_ok=False)
    versions={}
    for name,expected in [('dafny',gate.DAFNY_VERSION),('z3',gate.Z3_VERSION)]:
        p=subprocess.run([name,'--version'],capture_output=True,text=True,timeout=15)
        versions[name]=dict(exit_code=p.returncode,stdout=p.stdout,stderr=p.stderr)
        assert p.returncode==0 and p.stdout.strip()==expected
    write(output/'environment.json',dict(versions=versions,job_id=os.environ['SLURM_JOB_ID'],
        hostname=socket.gethostname(),utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        runtime_sha256=gate.sha((ROOT/'runtime-manifest.json').read_bytes()),
        fixture_sha256=gate.sha((ROOT/'fixture-manifest.json').read_bytes()),model_calls=0))
    observations=[]
    for case in json.loads((ROOT/'controls.json').read_bytes())['cases']:
        folder=ROOT/case['path'];files={p.name:p.read_bytes() for p in folder.glob('*.dfy')}
        profile=json.loads((folder/'profile.json').read_bytes())
        for mode in ['native','adapter'] + (['entry_only'] if case['id']=='omitted_failure' else []):
            name=case['id']+'-'+mode;run_id=os.environ['SLURM_JOB_ID']+':'+name
            record=gate.verify(files,profile,run_id) if mode=='adapter' else direct(files,profile,run_id,mode=='entry_only')
            archive(output,name,files,profile,record)
            row=dict(case=case['id'],mode=mode,run_id=run_id,exit_code=record['exit_code'],
                     elapsed_seconds=record['elapsed_seconds'],peak_rss_kib=record['peak_rss_kib'])
            observations.append(row);print(json.dumps(row),flush=True)
    check_pins();write(output/'summary.json',dict(model_calls=0,observations=observations,native_invocations=len(observations)))

if __name__=='__main__':main()
