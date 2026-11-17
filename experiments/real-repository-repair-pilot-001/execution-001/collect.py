"""One serial collection process; never launches a verifier or resumes a ledger."""
import json
import os
from pathlib import Path
import shutil
import sys
import time
from importlib.metadata import version

import common as c
from bounded_requests import RequestGate,bedrock_transport,consume_key,durable_json


def collect(out,transport,deadline,*,root=c.ROOT,clock=time.time,validate=None):
    validate=validate or (lambda: c.validate_package(root))
    _,tasks,order=validate()
    out=Path(out);out.mkdir(exist_ok=False)
    gate=RequestGate(out/'requests',c.LIMIT,deadline,transport,clock=clock)
    rows=[];ids=set();fatal=None
    try:
        for slot in order:
            validate()
            d=out/('slot-%02d'%slot['slot']);d.mkdir()
            request_file=root/'frozen-001'/slot['payload']
            shutil.copyfile(request_file,d/'request.json');durable_json(d/'slot.json',slot)
            start=clock()
            try:
                response=gate.invoke(c.read(request_file),task_id=slot['task'],attempt_id='slot-%02d'%slot['slot'])
            except BaseException as error:
                row=dict(**slot,outcome='REQUEST_STOP',error_type=type(error).__name__,elapsed_seconds=clock()-start)
                durable_json(d/'result.json',row);rows.append(row);fatal=type(error).__name__;break
            durable_json(d/'response.json',response)
            try:
                c.check_response_metadata(response,ids)
                extraction,candidate=c.classify_response(response,slot['task'],root)
            except (ValueError,TypeError,KeyError) as error:
                row=dict(**slot,outcome='RESPONSE_METADATA_STOP',error_type=type(error).__name__)
                durable_json(d/'result.json',row);rows.append(row);fatal=type(error).__name__;break
            durable_json(d/'extraction.json',extraction)
            if candidate is not None:
                with (d/'candidate.txt').open('xb') as f:f.write(candidate)
            row=dict(**slot,outcome=extraction['outcome'],request_id=response['request_id'],usage=response['usage'],
                     retry_attempts=response['retry_attempts'],stop_reason=response['stop_reason'],elapsed_seconds=clock()-start,
                     candidate_sha256=None if candidate is None else c.sha(d/'candidate.txt'))
            durable_json(d/'result.json',row);rows.append(row)
            durable_json(out/'results.json',rows)
            print('slot-%02d'%slot['slot'],row['outcome'],flush=True)
    except BaseException as error:
        fatal=type(error).__name__
    finally:
        complete=len(rows)==c.LIMIT and all(r['outcome'] in ('ADMITTED','OUTPUT_REJECTED','OUTPUT_TRUNCATED') for r in rows)
        if not gate.closed:gate.close('completed' if complete else 'stopped')
        reservations=gate.state['reservations']
        durable_json(out/'results.json',rows)
        summary=dict(status='COLLECTION_COMPLETE' if complete else 'COLLECTION_STOPPED',max_calls=c.LIMIT,
                     reserved=len(reservations),dispatch_started=sum('dispatch_started_at_epoch' in r for r in reservations),
                     completed_responses=sum(r['status']=='COMPLETED' for r in reservations),
                     ambiguous_or_unsaved=sum(r['status']=='AMBIGUOUS_OR_UNSAVED' for r in reservations),
                     unused_calls_not_reassigned=c.LIMIT-len(reservations),fatal_error_type=fatal,
                     result_rows=len(rows),admitted=sum(r['outcome']=='ADMITTED' for r in rows),
                     verifier_invocations=0,proposal_sha256=c.FREEZE_SHA)
        durable_json(out/'summary.json',summary)
    return summary


def main():
    c.require(sys.argv[1:]==['run'],'Only explicit fresh run supported')
    environment=c.compute_environment('collect');settings,_,_=c.validate_package();auth=c.authorization()
    c.require(not (c.ROOT/'model-001').exists(),'Existing collection cannot restart')
    environment.update(python=sys.version,packages={n:version(n) for n in ['boto3','botocore']},runtime_sha256=c.sha(c.ROOT/'runtime-freeze.json'))
    durable_json(c.ROOT/'collection-environment.json',environment)
    try:
        consume_key(Path.home()/'.repodisco-bedrock-handoff')
        summary=collect(c.ROOT/'model-001',bedrock_transport(settings),auth['expires_at_epoch'])
    except BaseException as error:
        durable_json(c.ROOT/'collection-startup-failure.json',dict(error_type=type(error).__name__,model_calls_not_inferred=True))
        raise RuntimeError('Collection stopped; inspect the preserved ledger and sanitized failure record') from None
    finally:
        os.environ.pop('AWS_BEARER_TOKEN_BEDROCK',None)
    c.require(summary['status']=='COLLECTION_COMPLETE','Collection stopped; no automatic recovery')


if __name__=='__main__':main()
