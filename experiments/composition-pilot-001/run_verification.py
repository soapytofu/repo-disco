"""Verify reference and negative controls; no model calls."""
import argparse
from datetime import datetime,timezone
import hashlib,json,shutil,subprocess,time,re
from pathlib import Path


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    source=Path(__file__).resolve().parent;out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    shutil.copytree(source/'tasks',out/'tasks');shutil.copy2(__file__,out/'runner.py')
    versions={}
    for name,command in [('dafny',['dafny','--version']),('z3',['z3','--version'])]:
        p=subprocess.run(command,text=True,capture_output=True,timeout=30);versions[name]={'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
    (out/'environment.json').write_text(json.dumps({'versions':versions,'started_at_utc':datetime.now(timezone.utc).isoformat(),'model_calls':0},indent=2)+'\n')
    rows=[]
    for task in sorted((out/'tasks').iterdir()):
        for variant in ['reference','missing','first_only','second_only','incorrect_composition']:
            folder=task/'fixtures'/variant;log=out/'checks'/task.name/variant;log.mkdir(parents=True)
            command=['dafny','verify','--verify-included-files','Client.dfy'];start=time.monotonic()
            try:
                p=subprocess.run(command,cwd=folder,text=True,capture_output=True,timeout=60);code,stdout,stderr=p.returncode,p.stdout,p.stderr
            except subprocess.TimeoutExpired as e:
                code=124;stdout=e.stdout or b'';stderr=e.stderr or b''
                stdout=stdout.decode(errors='replace') if isinstance(stdout,bytes) else stdout
                stderr=stderr.decode(errors='replace') if isinstance(stderr,bytes) else stderr
            (log/'stdout.txt').write_text(stdout);(log/'stderr.txt').write_text(stderr)
            m=re.search(r'(\d+) verified, (\d+) errors?',stdout)
            passed=code==0 and m is not None and int(m[1])>0 and int(m[2])==0
            failed=code==4 and m is not None and int(m[2])>0
            row={'task':task.name,'variant':variant,'command':command,'exit_code':code,'verified_obligations':int(m[1]) if m else None,'errors':int(m[2]) if m else None,'matches_expectation':passed if variant=='reference' else failed,'seconds':round(time.monotonic()-start,3),'source_hashes':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(folder.glob('*.dfy'))}}
            (log/'result.json').write_text(json.dumps(row,indent=2)+'\n');rows.append(row)
            (out/'results.json').write_text(json.dumps(rows,indent=2)+'\n')
            print(task.name,variant,code,'expected=',row['matches_expectation'],flush=True)
    good=all(r['matches_expectation'] for r in rows)
    (out/'summary.json').write_text(json.dumps({'checks':len(rows),'all_expected':good,'model_calls':0,'finished_at_utc':datetime.now(timezone.utc).isoformat()},indent=2)+'\n')
    if not good:raise SystemExit(1)
if __name__=='__main__':main()
