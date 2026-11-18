"""Fixed four-cell resource experiment; no model transport or credentials."""
import hashlib,json,os,socket
from pathlib import Path
ROOT=Path(__file__).resolve().parent
STAGES={'dafny-vmc':dict(cpus=1,memory_gb=2,minutes=30)}
ORDER=[('upstream',20000),('saved-candidate',20000),('saved-candidate',100000),('upstream',100000)]
def read(path):return json.loads(Path(path).read_bytes())
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def require(ok,message):
    if not ok:raise ValueError(message)
def check_pins(base,pins):
    for n,h in pins.items():
        p=Path(n);require(not p.is_absolute() and '..' not in p.parts and not (base/p).is_symlink(),'Unsafe pinned path')
        require(sha(base/p)==h,'Pinned bytes changed: '+n)
def validate_package(root=ROOT):
    runtime=read(root/'runtime-freeze.json')
    require(runtime['model_calls']==0 and runtime['native_invocations']==4,'Scope drift')
    check_pins(root,runtime['files'])
    plan=read(root/'plan.json');entries=plan['cases']
    require([(e['source'],e['resource_limit']) for e in entries]==ORDER,'Experiment matrix changed')
    require([e['slot'] for e in entries]==[1,2,3,4],'Order changed')
    for e in entries:
        require(e['wall_seconds']==300,'Wall cap changed')
        require(sha(root/'sources'/(e['source']+'.txt'))==e['candidate_sha256'],'Source changed')
    return {plan['task']['id']:plan['task']},entries
def compute_environment(stage):
    require(stage in STAGES and os.environ.get('SLURM_JOB_ID') and 'login' not in socket.gethostname().lower(),'Compute allocation required')
    require(int(os.environ.get('SLURM_CPUS_PER_TASK','0'))==1,'Serial one-core allocation required')
    return dict(stage=stage,job_id=os.environ['SLURM_JOB_ID'],host=socket.gethostname(),partition=os.environ.get('SLURM_JOB_PARTITION'),cpus=1,execution_root=str(ROOT))
def verification_observation(project,native,raw,base):
    from gates.vmc import protocol as dg
    from gates.vest import protocol_v2 as vg
    if project=='dafny-vmc':
        o=dg.dafny_observation(native['exit_code'],raw['stdout.txt'],raw['stderr.txt'],{n:b for n,b in raw.items() if n.startswith('csv/')},base['required_units'])
    else:o=vg.verus_observation(native['exit_code'],raw['stdout.txt'],raw['stderr.txt'],base['required'])
    o['warnings_match_upstream']=sorted(o['warnings'])==sorted(base['upstream_warnings'])
    o['qualified_scope_pass']=o['proof_pass'] and o['warnings_match_upstream']
    return json.loads(json.dumps(o))
