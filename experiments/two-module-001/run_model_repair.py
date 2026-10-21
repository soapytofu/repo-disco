"""Bounded repair pilot; stop on first protected whole-repository success."""
import argparse
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import time

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))
from botocore.config import Config
from langchain_aws import ChatBedrockConverse
from langchain_core.messages import HumanMessage, SystemMessage
from code_output_parser import CodeOutputParser
from repair_guard import validate_candidate

consume_key = runpy.run_path(str(ROOT/'experiments/repair-003/runner.py'),run_name='credential_helpers')['consume_key']


def save(path, value):
    temp = path.with_suffix(path.suffix+'.tmp')
    with temp.open('w') as f:
        json.dump(value,f,indent=2)
        f.write('\n'); f.flush(); os.fsync(f.fileno())
    os.replace(temp,path)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    source=Path(__file__).resolve().parent
    checks=source/'verification-001'
    assert json.loads((checks/'summary.json').read_text())['all_expected'], 'Baseline checks must pass before model calls'
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    shutil.copy2(__file__,out/'runner.py');shutil.copy2(source/'repair_guard.py',out/'repair_guard.py')
    manifest=(source/'repository-manifest.json').read_text()
    original=(source/'fixtures/implementation-bug/Arithmetic.dfy').read_text()
    client=(source/'fixtures/implementation-bug/Client.dfy').read_text()
    feedback=(checks/'checks/implementation-bug/whole_repository/stdout.txt').read_text()
    save(out/'protocol.json',dict(model='us.anthropic.claude-sonnet-4-6',region='us-east-1',max_calls=5,max_output_tokens=4096,temperature='provider_default',sdk_total_max_attempts=1,stop_on_first_success=True,verifier_timeout_seconds=60,model_request_retries=0,source_revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),packages={p:version(p) for p in ['langchain-aws','langchain-core','boto3','botocore']},started_at_utc=datetime.now(timezone.utc).isoformat()))
    (out/'repository-context.json').write_text(manifest)
    (out/'input-Arithmetic.dfy').write_text(original);(out/'protected-Client.dfy').write_text(client)
    (out/'input-verifier-output.txt').write_text(feedback)
    system=('Repair the two-module Dafny repository using its dependency map and verifier feedback. '
            'Return only the COMPLETE Arithmetic.dfy source, optionally in a dafny code fence. '
            'Change only the body of Arithmetic.Increment. Preserve its exact signature and ensures clause. '
            'Client.dfy is immutable, including both calls and assertions. Do not weaken contracts or introduce assumptions. '
            'For this fixture the allowed method body is one assignment y := arithmetic expression; '
            'using only x, integer literals, parentheses, and arithmetic operators. Do not add comments, attributes, or declarations.')
    rows=[];calls=0;current=None
    consume_key(Path.home()/'.repodisco-bedrock-handoff')
    try:
        model=ChatBedrockConverse(model='us.anthropic.claude-sonnet-4-6',region_name='us-east-1',max_tokens=4096,config=Config(connect_timeout=15,read_timeout=90,retries={'total_max_attempts':1}))
        for number in range(1,6):
            if (source/'STOP').exists(): break
            folder=out/f'attempt-{number:02d}';folder.mkdir()
            user=f'Repository map:\n{manifest}\nEditable Arithmetic.dfy:\n{original}\nProtected Client.dfy:\n{client}\nVerifier / previous-attempt feedback:\n{feedback}'
            save(folder/'prompt.json',[dict(role='system',content=system),dict(role='user',content=user)])
            current=dict(attempt=number,outcome='DISPATCHED');calls+=1
            save(out/'ledger.json',dict(calls_dispatched=calls,max_calls=5,completed=rows,current=current))
            try:
                response=model.invoke([SystemMessage(content=system),HumanMessage(content=user)])
            except Exception as error:
                current.update(outcome='API_ERROR',error_type=type(error).__name__)
                save(folder/'result.json',current);rows.append(current);current=None
                break
            current['usage']=response.usage_metadata
            save(folder/'response.json',dict(content=response.content,usage_metadata=response.usage_metadata,stop_reason=response.response_metadata.get('stopReason')))
            candidate=CodeOutputParser().invoke(response)
            (folder/'parsed-response.txt').write_text(candidate)
            try:
                validate_candidate(candidate)
            except ValueError as error:
                feedback=str(error);current.update(outcome='EDIT_REJECTED',reason=feedback)
            else:
                (folder/'Arithmetic.dfy').write_text(candidate)
                (folder/'Client.dfy').write_text(client)
                assert (folder/'Client.dfy').read_bytes()==client.encode()
                current['protected_client_sha256']=hashlib.sha256(client.encode()).hexdigest()
                current['verification']=[]
                for scope,files in [('provider',['Arithmetic.dfy']),('client_only',['Client.dfy']),('whole_repository',['--verify-included-files','Client.dfy'])]:
                    command=['dafny','verify']+files
                    start=time.monotonic()
                    try:
                        result=subprocess.run(command,cwd=folder,text=True,capture_output=True,timeout=60)
                        code,stdout,stderr=result.returncode,result.stdout,result.stderr
                    except subprocess.TimeoutExpired as error:
                        code=124
                        stdout=error.stdout or b'';stderr=error.stderr or b''
                        stdout=stdout.decode(errors='replace') if isinstance(stdout,bytes) else stdout
                        stderr=stderr.decode(errors='replace') if isinstance(stderr,bytes) else stderr
                    (folder/f'{scope}-stdout.txt').write_text(stdout);(folder/f'{scope}-stderr.txt').write_text(stderr)
                    current['verification'].append(dict(scope=scope,command=command,exit_code=code,seconds=round(time.monotonic()-start,3)))
                    if scope=='whole_repository': feedback=stdout+'\n'+stderr
                current['outcome']='SUCCESS' if all(r['exit_code']==0 for r in current['verification']) else 'VERIFICATION_FAILED'
            save(folder/'result.json',current);rows.append(current);current=None
            save(out/'ledger.json',dict(calls_dispatched=calls,max_calls=5,completed=rows,current=None))
            print('ATTEMPT',number,rows[-1]['outcome'],flush=True)
            if rows[-1]['outcome']=='SUCCESS':break
            if any(r['exit_code'] in (124,137) for r in rows[-1].get('verification',[])):break
    finally:
        os.environ.pop('AWS_BEARER_TOKEN_BEDROCK',None)
        save(out/'ledger.json',dict(calls_dispatched=calls,max_calls=5,completed=rows,current=current,finished_at_utc=datetime.now(timezone.utc).isoformat()))
    print('FINISHED calls=',calls,'credential cleared',flush=True)


if __name__=='__main__':main()
