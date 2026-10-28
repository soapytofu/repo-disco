"""One compute process for the authorized 20+8 calls; private key loaded once.

Existing frozen baseline/agent prompts and guards remain unchanged. This driver
adds stage ordering and a stop after any ambiguous or incomplete baseline stage.
It never resumes an existing run or reallocates unused calls between stages.
"""
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import time
import baseline_smoke as baseline
import repository_agent_pilot as pilot
from bounded_requests import RequestGate,bedrock_transport,consume_key
from repository_agent import RevisionStore,repair,atomic_json

ROOT=Path(__file__).resolve().parent
EXP=ROOT/'experiments/weeks1-4-continuation-001'

def stages(baseline_run,agent_run):
    results=baseline_run()
    if len(results)!=20 or any(r['outcome'] in ('REQUEST_STOP','TIMEOUT','KILLED','EXECUTION_ERROR') for r in results):
        return dict(status='STOPPED_AFTER_BASELINE',baseline=results,agent_started=False)
    return dict(status='STAGES_FINISHED',baseline=results,agent=agent_run(),agent_started=True)

def agent_stage(plan,transport):
    """Same frozen task order, message adapter, guards and repair loop as pilot."""
    out=pilot.EXP/'model-001';out.mkdir(exist_ok=False)
    shutil.copytree(pilot.EXP/'frozen-model-001',out/'frozen')
    record=json.loads((out/'frozen/freeze.json').read_text())
    for name in record['code_and_input_sha256']:
        dest=out/'snapshot'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,dest)
    gate=RequestGate(out/'requests',8,time.time()+1800,transport);rows=[]
    for family,condition in plan['order']:
        pilot.validate();base=pilot.files_at(pilot.EXP/'fixtures'/family/(condition+'_empty'))
        manifest,decode,guards=pilot.task_parts(family,condition,base)
        store=RevisionStore.create(out/(family+'-'+condition),base,manifest)
        records=repair(store,pilot.AgentGate(gate),decode,guards,attempt_limit=2)
        rows.append(dict(task=manifest['task_id'],attempts=records));atomic_json(out/'results.json',rows)
        if gate.closed or any(r['outcome'] in ('REQUEST_STOP','VERIFIER_STOP','PROMOTION_REJECTED') for r in records):break
    summary=dict(results=rows,reserved_calls=len(gate.state['reservations']),maximum_calls=8)
    atomic_json(out/'summary.json',summary);return summary

def main():
    if not os.environ.get('SLURM_JOB_ID') or 'login' in socket.gethostname():raise SystemExit('Compute node required')
    settings,_=baseline.validate_freeze(baseline.EXP/'frozen-smoke-001');plan=pilot.validate()
    auth=json.loads((EXP/'authorization.json').read_text())
    expected={'baseline_limit':20,'agent_limit':8,'total_limit':28,
              'driver_sha256':baseline.sha(Path(__file__).read_bytes()),
              'baseline_freeze_sha256':baseline.sha((baseline.EXP/'frozen-smoke-001/freeze.json').read_bytes()),
              'agent_freeze_sha256':baseline.sha((pilot.EXP/'frozen-model-001/freeze.json').read_bytes())}
    if any(auth.get(k)!=v for k,v in expected.items()):raise SystemExit('Authorization/freeze mismatch')
    gate_record=json.loads((pilot.EXP/'model-preflight-gate.json').read_text())
    if gate_record['expected_cases']!=4 or not gate_record['all_expected']:raise SystemExit('Agent controls not reviewed/passed')
    if plan['max_calls']!=8 or plan['max_calls_per_task']!=2 or plan['reassign_unused']:raise SystemExit('Agent budget mismatch')
    outputs=[EXP/'run-001',baseline.EXP/'smoke-001',pilot.EXP/'model-001']
    if any(p.exists() for p in outputs):raise SystemExit('Existing run: inspect ledgers; no automatic resume')
    versions={p:subprocess.check_output([p,'--version'],text=True).strip() for p in ['dafny','z3']}
    if '4.11.0' not in versions['dafny'] or '4.12.1' not in versions['z3']:raise SystemExit('Verifier versions changed')
    from code_output_parser import CodeOutputParser
    from importlib.metadata import version
    packages={p:version(p) for p in ['boto3','botocore','langchain-core']}
    out=outputs[0];out.mkdir(parents=True,exist_ok=False)
    shutil.copy2(__file__,out/'weeks14_continuation.py');shutil.copy2(EXP/'authorization.json',out/'authorization.json')
    atomic_json(out/'environment.json',dict(versions=versions,packages=packages,job_id=os.environ['SLURM_JOB_ID'],host=socket.gethostname()))
    consume_key(Path.home()/'.repodisco-bedrock-handoff')
    try:
        # One process retains the credential in memory for both bounded stages.
        result=stages(lambda:baseline.run(baseline.EXP/'frozen-smoke-001',baseline.EXP/'smoke-001',
                                         bedrock_transport(settings),parser=CodeOutputParser().parse),
                      lambda:agent_stage(plan,bedrock_transport(plan)))
        atomic_json(out/'summary.json',result)
    finally:os.environ.pop('AWS_BEARER_TOKEN_BEDROCK',None)

if __name__=='__main__':main()
