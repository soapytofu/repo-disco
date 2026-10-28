"""Offline single-process budget-gate prototype. No provider or live CLI wiring."""
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


class OfflineGate:
    """One object owns a fresh ledger; reopening, retry and process sharing forbidden.

    The injected transport in this experiment is always a fake. This prototype
    does not supply SDK retry controls, credential handling or worker integration.
    """
    def __init__(self, directory, limit, deadline, transport, clock=time.time):
        if type(limit) is not int or limit<1:raise ValueError('positive integer budget required')
        if not math.isfinite(deadline):raise ValueError('finite UTC epoch deadline required')
        self.directory=Path(directory);self.directory.mkdir(parents=True,exist_ok=False)
        self.transport=transport;self.clock=clock;self.limit=limit;self.deadline=deadline
        self.closed=False;self.lock=threading.Lock()
        self.state=dict(schema='offline-gate-v1',limit=limit,deadline=deadline,reservations=[],closed=False)
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
