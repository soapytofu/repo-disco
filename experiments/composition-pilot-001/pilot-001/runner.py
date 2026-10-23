"""Twelve single-request trials: three tasks, two repeats, two conditions. No automatic retries."""
import argparse
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import re
import runpy
import shutil
import subprocess
import sys
import time

ROOT=Path.cwd()
sys.path.insert(0,str(ROOT))
from botocore.config import Config
from langchain_aws import ChatBedrockConverse
from langchain_core.messages import HumanMessage,SystemMessage
from code_output_parser import CodeOutputParser
from pilot_support import make_prompt,validate,load_task
consume_key=runpy.run_path(str(ROOT/'experiments/repair-003/runner.py'),run_name='credential_helpers')['consume_key']


def save(path,value):
    temp=path.with_suffix(path.suffix+'.tmp')
    with temp.open('w') as f:
        json.dump(value,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
    os.replace(temp,path)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();source=Path(__file__).resolve().parent
    baseline=source/'verification-002'
    assert json.loads((baseline/'summary.json').read_text())['all_expected']
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    shutil.copy2(__file__,out/'runner.py');shutil.copy2(source/'pilot_support.py',out/'pilot_support.py')
    plan=json.loads((source/'plan.json').read_text())
    assert len(plan)==12
    save(out/'plan.json',plan)
    save(out/'protocol.json',dict(max_calls=12,tasks=3,repetitions_per_task_condition=2,model='us.anthropic.claude-sonnet-4-6',region='us-east-1',max_output_tokens=4096,temperature='provider_default',sdk_total_max_attempts=1,verifier_timeout_seconds=60,automatic_retries=0,independent_single_request_trials=True,randomized=False,condition_order='alternating paired order by task and repeat',normalization='strip outer whitespace and ensure one final newline before protected-byte guard',source_revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),packages={p:version(p) for p in ['langchain-aws','langchain-core','boto3','botocore']},started_at_utc=datetime.now(timezone.utc).isoformat()))
    inputs=out/'inputs';inputs.mkdir()
    for task in sorted(set(row['task'] for row in plan)):
        sources,mapping=load_task(source/'tasks'/task)
        target=inputs/task;target.mkdir()
        for name,text in sources.items():(target/name).write_text(text)
        save(target/'dependency-map.json',mapping)
        (target/'feedback.txt').write_text((baseline/'checks'/task/'missing/stdout.txt').read_text())
    rows=[];calls=0;current=None
    consume_key(Path.home()/'.repodisco-bedrock-handoff')
    try:
        model=ChatBedrockConverse(model='us.anthropic.claude-sonnet-4-6',region_name='us-east-1',max_tokens=4096,config=Config(connect_timeout=15,read_timeout=90,retries={'total_max_attempts':1}))
        for sequence,item in enumerate(plan,1):
            if (source/'STOP').exists():break
            folder=out/f"{sequence:02d}-{item['task']}-{item['condition']}-r{item['repeat']}";folder.mkdir()
            sources,mapping=load_task(source/'tasks'/item['task'])
            client=sources['Client.dfy']
            feedback=(baseline/'checks'/item['task']/'missing/stdout.txt').read_text()
            messages=make_prompt(item['condition'],sources,mapping,feedback);save(folder/'prompt.json',messages)
            current=dict(item,sequence=sequence,outcome='DISPATCHED');calls+=1
            save(out/'ledger.json',dict(calls_dispatched=calls,max_calls=12,completed=rows,current=current))
            try:
                response=model.invoke([SystemMessage(content=messages[0]['content']),HumanMessage(content=messages[1]['content'])])
            except Exception as error:
                current.update(outcome='API_ERROR',error_type=type(error).__name__)
                save(folder/'result.json',current);rows.append(current);current=None;break
            current['usage']=response.usage_metadata
            save(folder/'response.json',dict(content=response.content,usage_metadata=response.usage_metadata,stop_reason=response.response_metadata.get('stopReason')))
            raw=CodeOutputParser().invoke(response);(folder/'parsed-response.txt').write_text(raw)
            candidate=raw.strip()+'\n'
            try:
                body=validate(candidate,client)
            except ValueError as error:
                current.update(outcome='EDIT_REJECTED',reason=str(error))
            else:
                (folder/'Client.dfy').write_text(candidate)
                for name,text in sources.items():
                    if name!='Client.dfy':(folder/name).write_text(text)
                current['called_symbols']=re.findall(r'([A-Za-z_][A-Za-z_0-9]*\.[A-Za-z_][A-Za-z_0-9]*)\s*\(',body)
                current['source_sha256']={name:hashlib.sha256((folder/name).read_bytes()).hexdigest() for name in sources}
                command=['dafny','verify','--verify-included-files','Client.dfy'];start=time.monotonic()
                try:
                    result=subprocess.run(command,cwd=folder,text=True,capture_output=True,timeout=60)
                    code,stdout,stderr=result.returncode,result.stdout,result.stderr
                except subprocess.TimeoutExpired as error:
                    code=124;stdout=error.stdout or b'';stderr=error.stderr or b''
                    stdout=stdout.decode(errors='replace') if isinstance(stdout,bytes) else stdout
                    stderr=stderr.decode(errors='replace') if isinstance(stderr,bytes) else stderr
                (folder/'verifier-stdout.txt').write_text(stdout);(folder/'verifier-stderr.txt').write_text(stderr)
                match=re.search(r'(\d+) verified, (\d+) errors?',stdout)
                success=code==0 and match and int(match[1])>0 and int(match[2])==0
                current.update(outcome='SUCCESS' if success else ('TIMEOUT' if code in (124,137) else ('RESOLUTION_OR_PARSE_ERROR' if code==2 else 'PROOF_FAILURE' if code==4 else 'VERIFIER_ERROR')),command=command,exit_code=code,seconds=round(time.monotonic()-start,3))
            save(folder/'result.json',current);rows.append(current);current=None
            save(out/'ledger.json',dict(calls_dispatched=calls,max_calls=12,completed=rows,current=None))
            print(sequence,item['task'],item['condition'],rows[-1]['outcome'],flush=True)
            if rows[-1]['outcome']=='TIMEOUT':break
    finally:
        os.environ.pop('AWS_BEARER_TOKEN_BEDROCK',None)
        save(out/'ledger.json',dict(calls_dispatched=calls,max_calls=12,completed=rows,current=current,finished_at_utc=datetime.now(timezone.utc).isoformat()))
    print('FINISHED',calls,'calls; credential cleared',flush=True)


if __name__=='__main__':main()
