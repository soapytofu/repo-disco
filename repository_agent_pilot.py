"""Prepared eight-request agent pilot. No model execution without authorization.

Four development tasks, at most two feedback-driven attempts each; unused calls
are not reassigned. This tests integration, not a powered shared/separate effect.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import sys
import time

from bounded_requests import RequestGate,bedrock_transport,consume_key
from repository_agent import RevisionStore,repair,atomic_json

ROOT=Path(__file__).resolve().parent
EXP=ROOT/'experiments/repository-agent-001'
sys.path.insert(0,str(EXP/'guards'))
from provider_guard import parse_response as provider_parse
from branch_guard import parse_response as branch_parse

ORDER=[('branch','shared'),('inductive','separate'),('branch','separate'),('inductive','shared')]
PROTOCOL={
 'branch': 'Return one JSON object with exactly ClientA.dfy and ClientB.dfy, each containing the COMPLETE file as a string. Preserve every byte outside the empty proof bodies. Only proof bodies may change. Allowed statements: F.Case0A/Case1A/Case0B/Case1B(integer_expression); and if comparison { statements } with optional else/else if. Integer expressions: x, y, decimal integers, unary +/- and binary +/- with arithmetic parentheses. Comparisons: < <= > >= == !=. No parentheses around a whole comparison. No comments, assertions, assumptions, reveals, loops, declarations or other calls. Only exported names can verify. At most 64 statements and 2048 tokens per body; nesting 24.',
 'inductive': 'Return one JSON object with exactly Facts.dfy containing the COMPLETE file as a string. Change only bodies of the AppendA/AppendB lemmas that occur in this file. Preserve all definitions, headers, contracts, attributes, decreases clauses, exports and client files. Allowed statements: if comparison { statements } with optional else/else if; assert comparison; and self-recursive calls to the SAME lemma with two sequence expressions. Expressions: s, t, integers, [], Total(expression), length |expression|, indexing, slices, unary +/- and binary +/-, with arithmetic parentheses. Comparisons: < <= > >= == !=. No comments, assume, reveal, calc, declarations, loops or cross-helper calls. At most 64 statements and 2048 tokens per body; nesting 24. Automatic induction is disabled; explicit base/step reasoning may be necessary.'}

def files_at(folder):return {p.name:p.read_bytes() for p in folder.glob('*.dfy')}
def sha(data):return hashlib.sha256(data).hexdigest()

def task_parts(family,condition,base):
    editable=['Facts.dfy'] if family=='inductive' else ['ClientA.dfy','ClientB.dfy']
    deps={k:[] for k in base};deps.update({'All.dfy':['ClientA.dfy','ClientB.dfy'],'ClientA.dfy':['Facts.dfy'],'ClientB.dfy':['Facts.dfy']})
    manifest=dict(task_id=family+'-'+condition,entry='All.dfy',editable=editable,dependencies=deps,
                  context_policy='full_source_plus_declared_map',output_protocol=PROTOCOL[family])
    if family=='inductive':
        def decode(raw,snapshot):
            content,_=provider_parse(raw['text'],snapshot.files['Facts.dfy'].decode());return {'Facts.dfy':content.encode()}
        def guard(before,after):
            content,_=provider_parse(json.dumps({'Facts.dfy':after.decode()}),before.decode())
            if content.encode()!=after:raise ValueError('guard modified output')
        guards={'Facts.dfy':guard}
    else:
        def decode(raw,snapshot):
            content,_=branch_parse(raw['text'],{k:snapshot.files[k].decode() for k in editable})
            return {k:v.encode() for k,v in content.items()}
        guards={}
        for key in editable:
            def guard(before,after,key=key):
                originals={k:base[k].decode() for k in editable};content,_=branch_parse(json.dumps({**originals,key:after.decode()}),originals)
                if content[key].encode()!=after:raise ValueError('guard modified output')
            guards[key]=guard
    return manifest,decode,guards

def messages_for(context):
    return [dict(role='system',content='You are an expert Dafny developer. Repair the repository using the exact permitted output grammar. Preserve all required contracts. Return the requested JSON object only.'),
            dict(role='user',content=json.dumps(context,sort_keys=True,indent=2))]

class AgentGate:
    def __init__(self,gate):self.gate=gate
    def invoke(self,context,**identity):return self.gate.invoke(messages_for(context),**identity)

def freeze():
    bundle=EXP/'frozen-model-001';bundle.mkdir(exist_ok=False)
    sources=['repository_agent_pilot.py','repository_agent.py','bounded_requests.py',
             'language/__init__.py','language/dafny/__init__.py','language/dafny/prompt.py',
             'language/dafny/candidate.py','language/dafny/repository.py','execute.py']
    sources += [str(p.relative_to(ROOT)) for p in (EXP/'guards').glob('*.py')]
    sources += [str(p.relative_to(ROOT)) for family,condition in ORDER for p in (EXP/'fixtures'/family/(condition+'_empty')).glob('*.dfy')]
    plan=dict(order=ORDER,max_calls=8,max_calls_per_task=2,reassign_unused=False,automatic_retries=False,
              model_id='global.anthropic.claude-opus-4-5-20251101-v1:0',region='us-east-1',
              inference_config={'maxTokens':4096,'temperature':1.0},protocol=PROTOCOL,
              purpose='sequential agent integration on development tasks; not independent pass@2')
    atomic_json(bundle/'plan.json',plan)
    atomic_json(bundle/'freeze.json',dict(code_and_input_sha256={p:sha((ROOT/p).read_bytes()) for p in sources},plan_sha256=sha((bundle/'plan.json').read_bytes())))

def validate():
    bundle=EXP/'frozen-model-001';record=json.loads((bundle/'freeze.json').read_text())
    if sha((bundle/'plan.json').read_bytes())!=record['plan_sha256']:raise ValueError('plan changed')
    for name,digest in record['code_and_input_sha256'].items():
        if sha((ROOT/name).read_bytes())!=digest:raise ValueError('frozen source changed: '+name)
    return json.loads((bundle/'plan.json').read_text())

def main():
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['freeze','validate','run']);args=ap.parse_args()
    if args.mode=='freeze':freeze();return
    plan=validate()
    if args.mode=='validate':print('Eight-call agent plan validated; no requests');return
    if not os.environ.get('SLURM_JOB_ID') or 'login' in socket.gethostname():raise SystemExit('Compute node required')
    # Require the exact scripted agent control evidence reviewed before any paid run.
    gate_record=json.loads((EXP/'model-preflight-gate.json').read_text())
    if gate_record['expected_cases']!=4 or not gate_record['all_expected']:raise SystemExit('Agent preflight not passed')
    auth=json.loads((EXP/'model-authorization.json').read_text())
    if auth['max_calls']!=8 or auth['freeze_sha256']!=sha((EXP/'frozen-model-001/freeze.json').read_bytes()):raise SystemExit('Eight-call authorization required')
    out=EXP/'model-001';out.mkdir(exist_ok=False)
    shutil.copytree(EXP/'frozen-model-001',out/'frozen')
    record=json.loads((out/'frozen/freeze.json').read_text())
    for name in record['code_and_input_sha256']:
        dest=out/'snapshot'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,dest)
    from importlib.metadata import version
    versions={p:version(p) for p in ['boto3','botocore']}
    consume_key(Path.home()/'.repodisco-bedrock-handoff')
    try:
        gate=RequestGate(out/'requests',8,time.time()+1800,bedrock_transport(plan));rows=[]
        for family,condition in plan['order']:
            validate();base=files_at(EXP/'fixtures'/family/(condition+'_empty'))
            manifest,decode,guards=task_parts(family,condition,base)
            store=RevisionStore.create(out/(family+'-'+condition),base,manifest)
            results=repair(store,AgentGate(gate),decode,guards,attempt_limit=2)
            rows.append(dict(task=manifest['task_id'],attempts=results));atomic_json(out/'results.json',rows)
            if gate.closed or any(r['outcome'] in ['REQUEST_STOP','VERIFIER_STOP','PROMOTION_REJECTED'] for r in results):break
        atomic_json(out/'summary.json',dict(results=rows,reserved_calls=len(gate.state['reservations']),maximum_calls=8))
    finally:
        os.environ.pop('AWS_BEARER_TOKEN_BEDROCK',None)
        atomic_json(out/'environment.json',dict(packages=versions,job_id=os.environ['SLURM_JOB_ID'],host=socket.gethostname()))

if __name__=='__main__':main()
