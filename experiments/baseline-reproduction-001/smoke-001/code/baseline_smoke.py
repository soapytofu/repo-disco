"""Bounded DafnyBench baseline, using pinned checkout prompts/parser/patch logic.

Prepare is offline. Run is compute-only and requires a separately reviewed freeze
and private key. This is a 20-problem reimplementation smoke, not a paper score.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import tempfile
import time

from bounded_requests import RequestGate,bedrock_transport,consume_key,durable_json
from language.dafny.prompt import DafnyPromptBuilder
from patch import apply_text_diff,TEXT_BEFORE_EXAMPLE,TEXT_DIFF_EXAMPLE,TEXT_AFTER_EXAMPLE

ROOT=Path(__file__).resolve().parent
EXP=ROOT/'experiments/baseline-reproduction-001'
CODE=['baseline_smoke.py','bounded_requests.py','code_output_parser.py','patch.py',
      'language/__init__.py','language/dafny/__init__.py','language/dafny/prompt.py','execute.py']
def sha(data):return hashlib.sha256(data).hexdigest()
def save(path,value):durable_json(Path(path),value)

def prepare(dataset,preflight,destination):
    dataset=Path(dataset);preflight=Path(preflight);destination=Path(destination)
    summary=json.loads((preflight/'summary.json').read_text())
    manifest=json.loads((EXP/'dataset-manifest.json').read_text())
    if summary['total_files']!=len(manifest['files']) or summary['model_calls']!=0:
        raise ValueError('incomplete preflight')
    if sha((preflight/'dataset-manifest.json').read_bytes())!=sha((EXP/'dataset-manifest.json').read_bytes()):
        raise ValueError('preflight dataset identity mismatch')
    expected={r['path']:r for r in manifest['files']}
    selected=json.loads((preflight/'smoke-selection.json').read_text())
    eligible=json.loads((preflight/'eligible.json').read_text())
    ordered=sorted(eligible,key=lambda r:sha(('baseline-reproduction-001:'+r['path']).encode()))
    if selected!=ordered[:20] or len(selected)!=20 or len({r['path'] for r in selected})!=20:
        raise ValueError('selection/order mismatch')
    tasks=[]
    for index,item in enumerate(selected,1):
        name=item['path']
        if name not in expected or expected[name]['partition']!='hints_removed':raise ValueError('not an evaluation input')
        source=(dataset/name).read_bytes()
        if sha(source)!=expected[name]['sha256'] or sha(source)!=item['sha256']:raise ValueError('source hash mismatch')
        report=json.loads((preflight/'logs'/name).with_suffix('.json').read_text())
        if report['sha256']!=sha(source) or report['legacy_outcome']=='SUCCESS':raise ValueError('ineligible input')
        notes=f"Verifier stdout:\n{report['stdout']}\n\nVerifier stderr:\n{report['stderr']}\n"
        messages=DafnyPromptBuilder().repair(program=source.decode(),notes=notes,
            example_before=TEXT_BEFORE_EXAMPLE,example_diff=TEXT_DIFF_EXAMPLE,example_after=TEXT_AFTER_EXAMPLE)
        tasks.append(dict(sequence=index,path=name,source=source.decode(),source_sha256=sha(source),
                          initial_verification=report,messages=messages))
    destination.mkdir(parents=True,exist_ok=False)
    settings=dict(model_id='global.anthropic.claude-opus-4-5-20251101-v1:0',region='us-east-1',
                  inference_config=dict(maxTokens=4096,temperature=1.0),max_calls=20,attempts_per_problem=1,
                  sdk_total_max_attempts=1,no_automatic_retries=True,
                  scope='bounded reimplementation; not exact published numerical reproduction',
                  evaluation_policy='pinned checkout diff parser; report specification audit separately')
    save(destination/'settings.json',settings);save(destination/'tasks.json',tasks)
    shutil.copy2(preflight/'summary.json',destination/'preflight-summary.json')
    save(destination/'freeze.json',dict(code_sha256={p:sha((ROOT/p).read_bytes()) for p in CODE},
         artifact_sha256={p:sha((destination/p).read_bytes()) for p in ['settings.json','tasks.json','preflight-summary.json']},
         dataset_revision=manifest['revision'],model_calls=0))
    return tasks

def validate_freeze(bundle):
    bundle=Path(bundle);freeze=json.loads((bundle/'freeze.json').read_text())
    for name,digest in freeze['code_sha256'].items():
        if sha((ROOT/name).read_bytes())!=digest:raise ValueError('code freeze mismatch: '+name)
    for name,digest in freeze['artifact_sha256'].items():
        if sha((bundle/name).read_bytes())!=digest:raise ValueError('artifact freeze mismatch: '+name)
    settings=json.loads((bundle/'settings.json').read_text());tasks=json.loads((bundle/'tasks.json').read_text())
    if settings['max_calls']!=20 or settings['attempts_per_problem']!=1 or len(tasks)!=20:
        raise ValueError('smoke budget mismatch')
    return settings,tasks

def verify_source(source):
    # A single-file baseline must not read arbitrary cluster files via includes.
    # This conservative additional rejection is disclosed and counted separately.
    if re.search(r'\binclude\b',source):return dict(exit_code=None,category='EXTERNAL_INCLUDE_REJECTED',stdout='',stderr='')
    with tempfile.TemporaryDirectory(prefix='baseline-smoke-') as temp:
        (Path(temp)/'program.dfy').write_text(source)
        proc=subprocess.run(['timeout','-k','5s','10s','dafny','verify','program.dfy'],cwd=temp,capture_output=True,text=True)
    legacy='SUCCESS' if '0 errors' in proc.stdout else 'GOAL_UNPROVEN' if 'postcondition' in proc.stdout else 'FAIL'
    return dict(exit_code=proc.returncode,legacy_outcome=legacy,stdout=proc.stdout,stderr=proc.stderr,
                category={0:'VERIFIED',4:'PROOF_FAILURE',2:'FRONTEND_ERROR',124:'TIMEOUT',137:'KILLED'}.get(proc.returncode,'EXECUTION_ERROR'))

def evaluate(task,response,folder,*,parser,verifier=verify_source):
    folder=Path(folder);source=task['source']
    try:
        diff=parser(response['text']).strip();(folder/'patch.txt').write_text(diff)
        candidate=apply_text_diff(source,diff)
    except Exception as error:
        return dict(outcome='PATCH_REJECTED',error_type=type(error).__name__,success=False)
    (folder/'candidate.dfy').write_text(candidate)
    # Flags aid manual review, not a semantic contract-preservation guarantee.
    audit=dict(manual_review_required=True,source_changed=candidate!=source,
               bypass_terms_present=bool(re.search(r'\b(?:assume|axiom)\b|verify\s+false',candidate)),
               original_sha256=sha(source.encode()),candidate_sha256=sha(candidate.encode()))
    save(folder/'audit.json',audit)
    result=verifier(candidate);save(folder/'verification.json',result)
    return dict(outcome=result['category'],success=result.get('legacy_outcome')=='SUCCESS',
                strict_exit_success=result['exit_code']==0,manual_specification_review_required=True)

def run(bundle,out,transport,*,parser,verifier=verify_source,clock=time.time):
    settings,tasks=validate_freeze(bundle);out=Path(out);out.mkdir(parents=True,exist_ok=False)
    shutil.copytree(bundle,out/'frozen')
    for name in CODE:
        dest=out/'code'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,dest)
    gate=RequestGate(out/'requests',20,clock()+3600,transport,clock=clock);results=[]
    for task in tasks:
        validate_freeze(bundle)
        folder=out/f"{task['sequence']:02d}";folder.mkdir();save(folder/'task.json',task)
        try:response=gate.invoke(task['messages'],task_id=task['path'],attempt_id='1')
        except Exception as error:
            row=dict(sequence=task['sequence'],path=task['path'],outcome='REQUEST_STOP',error_type=type(error).__name__,success=False)
            save(folder/'result.json',row);results.append(row);break
        save(folder/'response.json',response)
        result=evaluate(task,response,folder,parser=parser,verifier=verifier)
        row=dict(sequence=task['sequence'],path=task['path'],**result);save(folder/'result.json',row);results.append(row)
        save(out/'results.json',results);print(task['sequence'],result['outcome'],flush=True)
        if result['outcome'] in ('TIMEOUT','KILLED','EXECUTION_ERROR'):break
    save(out/'summary.json',dict(results=results,reserved_calls=len(gate.state['reservations']),
         completed_tasks=len(results),budget=20,legacy_verified=sum(r['success'] for r in results),
         faithful_annotation_success_not_yet_audited=True))
    return results

def main():
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['prepare','validate','run'])
    ap.add_argument('--dataset',type=Path);ap.add_argument('--preflight',type=Path);args=ap.parse_args()
    bundle=EXP/'frozen-smoke-001'
    if args.mode=='prepare':prepare(args.dataset,args.preflight,bundle);return
    settings,_=validate_freeze(bundle)
    if args.mode=='validate':print('Frozen twenty-call smoke validated; no requests');return
    if not os.environ.get('SLURM_JOB_ID') or 'login' in socket.gethostname():raise SystemExit('Compute node required')
    out=EXP/'smoke-001'
    if out.exists():raise SystemExit('Existing run: inspect ledger, never restart')
    auth=json.loads((EXP/'smoke-authorization.json').read_text())
    if auth['max_calls']!=20 or auth['freeze_sha256']!=sha((bundle/'freeze.json').read_bytes()):raise SystemExit('Review/authorization mismatch')
    from code_output_parser import CodeOutputParser
    parser=CodeOutputParser().parse
    # Import/version checks precede credential consumption and request reservations.
    import boto3
    from botocore.config import Config
    from importlib.metadata import version
    versions={p:version(p) for p in ['boto3','botocore','langchain-core']}
    consume_key(Path.home()/'.repodisco-bedrock-handoff')
    try:run(bundle,out,bedrock_transport(settings),parser=parser)
    finally:
        os.environ.pop('AWS_BEARER_TOKEN_BEDROCK',None)
        if out.exists():save(out/'environment.json',dict(packages=versions,job_id=os.environ['SLURM_JOB_ID'],host=socket.gethostname()))

if __name__=='__main__':main()
