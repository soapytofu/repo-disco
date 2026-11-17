"""Verifier-only diagnostic; no provider, credentials or paid authorization."""
import hashlib,json,os,socket
from pathlib import Path
ROOT=Path(__file__).resolve().parent
STAGES={'dafny-vmc':dict(cpus=1,memory_gb=2,minutes=30),'vest':dict(cpus=4,memory_gb=4,minutes=60)}
def read(path):return json.loads(Path(path).read_bytes())
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def require(ok,message):
    if not ok:raise ValueError(message)
def check_pins(base,pins):
    for n,h in pins.items():
        p=Path(n);require(not p.is_absolute() and '..' not in p.parts and not (base/p).is_symlink(),'Unsafe pinned path')
        require(sha(base/p)==h,'Pinned bytes changed: '+n)
def validate_package(root=ROOT):
    runtime=read(root/'runtime-freeze.json');require(runtime['model_calls']==0 and runtime['native_invocations']==3,'Scope drift')
    check_pins(root,runtime['files'])
    from prepare import replay
    report,groups=replay(root)
    require(report==read(root/'offline-replay.json'),'Replay changed')
    plan=read(root/'plan.json');require(plan['groups']==groups and plan['model_calls']==0 and plan['native_invocations']==3,'Plan changed')
    return {t['id']:t for t in read(root/'tasks.json')},groups

def compute_environment(stage):
    require(stage in STAGES,'Unknown stage')
    require(os.environ.get('SLURM_JOB_ID') and 'login' not in socket.gethostname().lower(),'Compute allocation required')
    require(int(os.environ.get('SLURM_CPUS_PER_TASK','0'))==STAGES[stage]['cpus'],'Wrong CPU allocation')
    return dict(stage=stage,job_id=os.environ['SLURM_JOB_ID'],host=socket.gethostname(),partition=os.environ.get('SLURM_JOB_PARTITION'),
                cpus=STAGES[stage]['cpus'],execution_root=str(ROOT))

def verification_observation(project,native,raw,base):
    from gates.vmc import protocol as dg
    from gates.vest import protocol_v2 as vg
    if project=='dafny-vmc':
        o=dg.dafny_observation(native['exit_code'],raw['stdout.txt'],raw['stderr.txt'],{n:b for n,b in raw.items() if n.startswith('csv/')},base['required_units'])
    else:
        o=vg.verus_observation(native['exit_code'],raw['stdout.txt'],raw['stderr.txt'],base['required'])
    o['warnings_match_upstream']=sorted(o['warnings'])==sorted(base['upstream_warnings'])
    o['qualified_scope_pass']=o['proof_pass'] and o['warnings_match_upstream']
    return json.loads(json.dumps(o))
