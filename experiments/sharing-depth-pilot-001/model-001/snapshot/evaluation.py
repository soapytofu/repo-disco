"""Compute-only evaluation using the frozen tolerant parser."""
import hashlib,json,os,re,socket,subprocess,time
from pathlib import Path
from parser import parse_response,extract
ROOT=Path(__file__).resolve().parent
CLIENTS=('ClientA.dfy','ClientB.dfy')

def verify(folder, entry, timeout=60):
    if not os.environ.get('SLURM_JOB_ID') or 'login' in socket.gethostname():
        raise RuntimeError('Verification requires a Slurm compute node')
    cmd = ['dafny','verify','--verify-included-files',entry]
    start = time.monotonic()
    try:
        proc = subprocess.run(cmd,cwd=folder,text=True,capture_output=True,timeout=timeout)
        code, stdout, stderr = proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired as error:
        code = 124
        stdout, stderr = error.stdout or b'', error.stderr or b''
        stdout = stdout.decode(errors='replace') if isinstance(stdout,bytes) else stdout
        stderr = stderr.decode(errors='replace') if isinstance(stderr,bytes) else stderr
    match = re.search(r'(\d+) verified, (\d+) errors?',stdout)
    outcome = 'VERIFIER_ERROR'
    if code == 0 and match and int(match[1]) > 0 and int(match[2]) == 0:
        outcome = 'SUCCESS'
    elif code in (124,137):
        outcome = 'TIMEOUT'
    elif code == 2:
        outcome = 'RESOLUTION_OR_PARSE_ERROR'
    elif code == 4 and match and int(match[2]) > 0:
        outcome = 'PROOF_FAILURE'
    return dict(command=cmd,exit_code=code,outcome=outcome,seconds=round(time.monotonic()-start,3),stdout=stdout,stderr=stderr)


def evaluate(trial,raw,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    (out/'response.txt').write_text(raw)
    source=ROOT/trial['fixture'];originals={n:(source/n).read_text() for n in CLIENTS}
    try:
        _,extraction=extract(raw)
    except (ValueError,TypeError) as error:
        result=dict(outcome='FORMAT_REJECTED',reason=str(error),verification=[],extraction_accepted=False,guard_accepted=False)
    else:
        try:candidates,extraction=parse_response(raw,originals)
        except (ValueError,TypeError) as error:
            result=dict(outcome='EDIT_REJECTED',reason=str(error),verification=[],extraction=extraction,extraction_accepted=True,guard_accepted=False)
        else:
            for f in source.glob('*.dfy'):(out/f.name).write_bytes(candidates[f.name].encode() if f.name in candidates else f.read_bytes())
            checks=[]
            for entry in ('All.dfy',*CLIENTS):
                check=verify(out,entry)
                for stream in ('stdout','stderr'):(out/(entry+'.'+stream+'.txt')).write_text(check.pop(stream))
                checks.append(dict(entry=entry,**check))
                if check['outcome'] in ('TIMEOUT','VERIFIER_ERROR'):break
            outcome='SUCCESS' if len(checks)==3 and all(c['outcome']=='SUCCESS' for c in checks) else next(c['outcome'] for c in checks if c['outcome']!='SUCCESS')
            result=dict(outcome=outcome,verification=checks,extraction=extraction,extraction_accepted=True,guard_accepted=True,source_sha256={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(out.glob('*.dfy'))})
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    return result
