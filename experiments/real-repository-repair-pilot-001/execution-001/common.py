"""Closed sixteen-slot scope and source-bound evaluation; no transport on import."""
import collections
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import socket
import time

ROOT = Path(__file__).resolve().parent
FREEZE_SHA = '0b28485bde1d52137afe217db690e6c672f9444eb04a6300d069c3b0b4884556'
LIMIT = 16
QUAL_REL = Path('experiments/real-repository-qualification-001')
PILOT_REL = Path('experiments/real-repository-repair-pilot-001')
STAGES = {'collect': dict(cpus=1, memory_gb=2, minutes=60),
          'dafny-vmc': dict(cpus=1, memory_gb=2, minutes=30),
          'vest': dict(cpus=4, memory_gb=4, minutes=150)}


def read(path): return json.loads(Path(path).read_bytes())
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def require(ok, message):
    if not ok: raise ValueError(message)


def check_pins(base, pins):
    for name, expected in pins.items():
        p = Path(name)
        require(not p.is_absolute() and '..' not in p.parts and not (base/p).is_symlink(), 'Unsafe pinned path')
        require(sha(base/p) == expected, 'Pinned bytes changed: '+name)


def validate_package(root=ROOT, *, runtime=True):
    f = root/'frozen-001'
    require(sha(f/'manifest.json') == FREEZE_SHA, 'Approved proposal digest changed')
    pins = read(f/'manifest.json'); check_pins(f, pins)
    require({p.relative_to(f).as_posix() for p in f.rglob('*') if p.is_file()} == set(pins)|{'manifest.json'}, 'Frozen artifact set changed')
    check_pins(root/'inputs', read(f/'inputs.json'))
    settings = read(f/'settings.json'); scope = read(f/'scope.json'); order = read(f/'order.json')
    require(scope['proposed_max_new_requests']==LIMIT and not scope['automatic_retries'] and not scope['reassign_unused'], 'Budget drift')
    require([x['slot'] for x in order] == list(range(1,LIMIT+1)), 'Slot order drift')
    require(set(collections.Counter((x['task'],x['arm']) for x in order).values())=={2}, 'Unbalanced scope')
    require(len({x['task'] for x in order})==4 and all(x['max_requests']==1 and x['independent_context'] for x in order), 'Trial scope drift')
    original=root/'inputs'/PILOT_REL
    for name in ['body_guard.py','extract_response.py','tasks.json']:
        require((root/name).read_bytes()==(original/name).read_bytes(), 'Policy copy changed')
    for p in (root/'fixtures').rglob('*'):
        if p.is_file(): require(p.read_bytes()==(original/p.relative_to(root)).read_bytes(),'Fixture copy changed')
    tasks={t['id']:t for t in read(root/'tasks.json')}
    require(set(tasks)=={x['task'] for x in order}, 'Task IDs changed')
    gate=read(original/'controls-review-001.json')
    require(gate['status']=='ALL_SIX_NEGATIVE_CONTROLS_MATCH' and gate['new_verifier_invocations']==6,'Readiness gate absent')
    if runtime:
        r=read(root/'runtime-freeze.json')
        require(r['proposal_sha256']==FREEZE_SHA and r['max_calls']==LIMIT and not r['retries'] and not r['reassign_unused'],'Runtime scope drift')
        check_pins(root,r['files'])
    return settings,tasks,order


def authorization(root=ROOT, now=None):
    now=time.time() if now is None else now
    a=read(root/'authorization.json')
    require(a.get('authorized') is True and a.get('max_calls')==LIMIT and a.get('retries') is False and a.get('reassign_unused') is False,'Fresh sixteen-call approval required')
    require(a.get('proposal_sha256')==FREEZE_SHA and a.get('runtime_sha256')==sha(root/'runtime-freeze.json'),'Authorization pins changed')
    expiry=a.get('expires_at_epoch')
    require(type(expiry) in (int,float) and math.isfinite(expiry) and now<expiry<=now+86400,'Authorization expired')
    require(isinstance(a.get('human_basis'),str) and a['human_basis'],'Missing human approval basis')
    return a


def compute_environment(stage):
    require(stage in STAGES,'Unknown stage')
    require(os.environ.get('SLURM_JOB_ID') and 'login' not in socket.gethostname().lower(),'Compute allocation required')
    require(int(os.environ.get('SLURM_CPUS_PER_TASK','0'))==STAGES[stage]['cpus'],'Wrong CPU allocation')
    return dict(stage=stage,job_id=os.environ['SLURM_JOB_ID'],host=socket.gethostname(),
                partition=os.environ.get('SLURM_JOB_PARTITION'),cpus=STAGES[stage]['cpus'],
                proposal_sha256=FREEZE_SHA,execution_root=str(ROOT))


def guard_for(root=ROOT):
    spec=importlib.util.spec_from_file_location('real_repair_frozen_guard',root/'body_guard.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def classify_response(response,tid,root=ROOT):
    require(isinstance(response.get('text'),str),'Missing response text')
    if response.get('stop_reason')=='max_tokens':return dict(outcome='OUTPUT_TRUNCATED',accepted=False),None
    require(response.get('stop_reason')=='end_turn','Unsupported provider stop reason')
    try:
        candidate,receipt=guard_for(root).parse_response(response['text'],tid)
    except (ValueError,TypeError,UnicodeError,RecursionError) as e:
        return dict(outcome='OUTPUT_REJECTED',accepted=False,error_type=type(e).__name__,reason=str(e)),None
    return dict(outcome='ADMITTED',accepted=True,receipt=receipt),candidate


def check_response_metadata(response,ids):
    rid=response.get('request_id')
    require(isinstance(rid,str) and rid and rid not in ids,'Missing or duplicate request ID')
    require(response.get('retry_attempts')==0,'SDK retry or absent retry metadata')
    usage=response.get('usage')
    require(isinstance(usage,dict) and all(type(usage.get(k)) is int and usage[k]>=0 for k in ['inputTokens','outputTokens','totalTokens']),'Missing token usage')
    require(usage['totalTokens']==usage['inputTokens']+usage['outputTokens'],'Token totals disagree')
    ids.add(rid)


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
