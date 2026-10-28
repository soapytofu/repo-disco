"""Single-owner durable request ledger and explicit no-retry Bedrock transport.

Additive implementation derived from the frozen offline-gate experiment.
"""
import json
import math
import os
from pathlib import Path
import threading
import time


class GateClosed(RuntimeError): pass


def durable_json(path, value):
    data=json.dumps(value,ensure_ascii=False,allow_nan=False,indent=2)+'\n'
    temporary=path.with_suffix('.tmp')
    with temporary.open('x') as stream:
        stream.write(data);stream.flush();os.fsync(stream.fileno())
    os.replace(temporary,path)
    fd=os.open(path.parent,os.O_RDONLY)
    try:os.fsync(fd)
    finally:os.close(fd)


class RequestGate:
    """One object owns a fresh ledger; reopening, retry and process sharing forbidden.

    One process owns a fresh run. Every worker repair must use this same object.
    Restart/resume requires manual ledger review; this class never resumes.
    """
    def __init__(self, directory, limit, deadline, transport, clock=time.time):
        if type(limit) is not int or limit<1:raise ValueError('positive integer budget required')
        if not math.isfinite(deadline):raise ValueError('finite UTC epoch deadline required')
        self.directory=Path(directory);self.directory.mkdir(parents=True,exist_ok=False)
        self.transport=transport;self.clock=clock;self.limit=limit;self.deadline=deadline
        self.closed=False;self.lock=threading.Lock()
        self.state=dict(schema='bounded-requests-v1',limit=limit,deadline=deadline,reservations=[],closed=False)
        durable_json(self.directory/'ledger.json',self.state)

    def close(self,reason):
        self.closed=True;self.state.update(closed=True,closed_reason=reason)
        durable_json(self.directory/'ledger.json',self.state)

    def invoke(self,prompt,*,task_id,attempt_id):
        if not self.lock.acquire(blocking=False):raise GateClosed('concurrent/reentrant invocation unsupported')
        try:
            if self.closed:raise GateClosed('gate closed')
            if self.clock()>=self.deadline:
                self.close('deadline');raise GateClosed('deadline reached')
            if len(self.state['reservations'])>=self.limit:
                self.close('budget');raise GateClosed('budget exhausted')
            # Validate and copy before reservation; no transport sees caller-owned data.
            payload=json.loads(json.dumps(dict(prompt=prompt,task_id=task_id,attempt_id=attempt_id),allow_nan=False))
            number=len(self.state['reservations'])+1
            record=dict(sequence=number,status='RESERVED',**payload)
            self.state['reservations'].append(record)
            self.closed=True  # Any persistence failure leaves this instance closed.
            durable_json(self.directory/'ledger.json',self.state)
            # Disk work may cross the deadline. Reservation stays consumed.
            if self.clock()>=self.deadline:
                self.close('deadline_before_transport');raise GateClosed('deadline reached')
            try:
                response=self.transport(json.loads(json.dumps(payload['prompt'],allow_nan=False)))
                durable_json(self.directory/f'response-{number:03}.json',response)
            except BaseException as error:
                record.update(status='AMBIGUOUS_OR_UNSAVED',error_type=type(error).__name__)
                self.close('transport_or_response_failure')
                raise
            record['status']='COMPLETED'
            durable_json(self.directory/'ledger.json',self.state)
            self.closed=False
            return response
        finally:self.lock.release()


def converse_request(messages, settings):
    if not messages or any(set(m)!={'role','content'} or not isinstance(m['content'],str) for m in messages):
        raise ValueError('text chat messages required')
    system=[];chat=[]
    for message in messages:
        if message['role']=='system':
            if chat:raise ValueError('system messages must precede conversation')
            system.append({'text':message['content']})
        elif message['role'] in ('user','assistant'):
            chat.append(dict(role=message['role'],content=[{'text':message['content']}]))
        else:raise ValueError('unsupported role')
    if not chat or chat[0]['role']!='user':raise ValueError('user message required')
    inference=settings['inference_config']
    if set(inference)!={'maxTokens','temperature'} or type(inference['maxTokens']) is not int or not 1<=inference['maxTokens']<=10000 or not 0<=inference['temperature']<=1:
        raise ValueError('explicit bounded inference configuration required')
    return dict(modelId=settings['model_id'],system=system,messages=chat,inferenceConfig=dict(inference))


def bedrock_transport(settings, *, client_factory=None, config_factory=None):
    """One SDK Converse call per invocation; no streaming, tools, or retries.

    Factories permit offline inspection of SDK configuration. Credentials must
    already have been loaded privately by the caller; never serialize the client.
    """
    if client_factory is None:
        import boto3
        client_factory=boto3.client
    if config_factory is None:
        from botocore.config import Config
        config_factory=Config
    config=config_factory(connect_timeout=15,read_timeout=180,retries={'mode':'standard','total_max_attempts':1})
    client=client_factory('bedrock-runtime',region_name=settings['region'],config=config)
    def invoke(messages):
        response=client.converse(**converse_request(messages,settings))
        blocks=response['output']['message']['content']
        return dict(text=''.join(b['text'] for b in blocks if 'text' in b),content=blocks,
                    usage=response.get('usage'),stop_reason=response.get('stopReason'),
                    request_id=response.get('ResponseMetadata',{}).get('RequestId'),
                    retry_attempts=response.get('ResponseMetadata',{}).get('RetryAttempts'))
    return invoke


def consume_key(path):
    """Consume the account-private handoff without displaying or archiving it."""
    import stat
    path=Path(path);fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    with os.fdopen(fd) as stream:
        info=os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid() or info.st_mode&0o077 or info.st_size>65536:
            raise ValueError('unsafe key handoff')
        token=stream.read().strip()
    if not token:raise ValueError('empty key handoff')
    path.unlink();os.environ['AWS_BEARER_TOKEN_BEDROCK']=token
