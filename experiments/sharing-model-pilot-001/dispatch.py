"""Bounded eight-request adapter. Fixed live output directory prevents restart."""
from datetime import datetime,timezone
import json,os,shutil,socket,stat
from pathlib import Path
from harness import ROOT,request_for,evaluate
from pilot import verify_freeze

def save(path,value):
    temp=path.with_suffix(path.suffix+'.tmp')
    with temp.open('w') as f:
        json.dump(value,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
    os.replace(temp,path)
    fd=os.open(path.parent,os.O_RDONLY)
    try:os.fsync(fd)
    finally:os.close(fd)

def run_batch(out,transport,evaluator=evaluate):
    verify_freeze()
    requests=[request_for(i) for i in range(1,9)]
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    snapshot=out/'snapshot';snapshot.mkdir()
    for name in ['dispatch.py','authorization.json','plan.json','protocol.json','frozen-bundle.json','harness.py','pilot.py']:
        shutil.copy2(ROOT/name,snapshot/name)
    for name in ['prompts','fixtures']:shutil.copytree(ROOT/name,snapshot/name)
    state=dict(max_calls=8,calls_dispatched=0,completed=[],current=None,started_at_utc=datetime.now(timezone.utc).isoformat())
    save(out/'ledger.json',state)
    for trial,messages in requests:
        folder=out/f"{trial['sequence']:02d}-{trial['condition']}-r{trial['repeat']}";folder.mkdir()
        save(folder/'prompt.json',messages)
        state['calls_dispatched']+=1
        state['current']=dict(trial,status='DISPATCHED')
        save(out/'ledger.json',state) # durable before any network request
        try:
            response=transport(messages)
        except Exception as error:
            result=dict(trial,outcome='API_ERROR',error_type=type(error).__name__,request_outcome_may_be_ambiguous=True)
            save(folder/'result.json',result)
            state['completed'].append(result);state['current']=None
            save(out/'ledger.json',state);break
        save(folder/'response.json',response)
        try:
            result=evaluator(trial['condition'],response['text'],folder/'evaluation')
        except Exception as error:
            result=dict(outcome='VERIFIER_ERROR',error_type=type(error).__name__)
        result=dict(trial,**result,usage=response.get('usage'),stop_reason=response.get('stop_reason'))
        save(folder/'result.json',result)
        state['completed'].append(result);state['current']=None
        save(out/'ledger.json',state)
        print(trial['sequence'],trial['condition'],result['outcome'],flush=True)
        if result['outcome'] in ('TIMEOUT','VERIFIER_ERROR'):break
    state['finished_at_utc']=datetime.now(timezone.utc).isoformat()
    state['all_eight_dispatched']=state['calls_dispatched']==8
    save(out/'ledger.json',state)
    return state

def consume_key():
    path=Path.home()/'.repodisco-bedrock-handoff'
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    with os.fdopen(fd) as f:
        info=os.fstat(f.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid() or info.st_mode & 0o077 or info.st_size>65536:
            raise RuntimeError('Unsafe key handoff')
        token=f.read().strip()
    if not token:raise RuntimeError('Empty key')
    path.unlink();os.environ['AWS_BEARER_TOKEN_BEDROCK']=token

def main():
    if not os.environ.get('SLURM_JOB_ID') or 'login' in socket.gethostname():raise SystemExit('Compute node required')
    verify_freeze()
    auth=json.loads((ROOT/'authorization.json').read_text())
    if auth['authorized_calls']!=8:raise SystemExit('Eight-call authorization required')
    preflight=json.loads((ROOT/'preflight-001/summary.json').read_text())
    if not preflight['all_expected'] or preflight['verifier_checks']!=12:raise SystemExit('Preflight gate failed')
    out=ROOT/'model-001'
    if out.exists():raise SystemExit('Existing run: inspect ledger; never restart or duplicate')
    from botocore.config import Config
    from langchain_aws import ChatBedrockConverse
    from langchain_core.messages import SystemMessage,HumanMessage
    consume_key()
    try:
        model=ChatBedrockConverse(model='us.anthropic.claude-sonnet-4-6',region_name='us-east-1',max_tokens=4096,config=Config(connect_timeout=15,read_timeout=90,retries={'total_max_attempts':1}))
        def transport(messages):
            response=model.invoke([SystemMessage(content=messages[0]['content']),HumanMessage(content=messages[1]['content'])])
            content=response.content
            text=content if isinstance(content,str) else ''.join(b.get('text','') for b in content if isinstance(b,dict) and b.get('type')=='text')
            return dict(content=content,text=text,usage=response.usage_metadata,stop_reason=response.response_metadata.get('stopReason'),request_id=response.response_metadata.get('ResponseMetadata',{}).get('RequestId'))
        run_batch(out,transport)
    finally:
        os.environ.pop('AWS_BEARER_TOKEN_BEDROCK',None)
        if out.exists():
            from importlib.metadata import version
            save(out/'environment.json',dict(host=socket.gethostname(),job_id=os.environ['SLURM_JOB_ID'],sdk_total_max_attempts=1,packages={p:version(p) for p in ['boto3','botocore','langchain-aws','langchain-core']}))
if __name__=='__main__':main()
