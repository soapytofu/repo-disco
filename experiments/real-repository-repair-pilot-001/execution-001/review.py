"""Offline replay of request provenance, protected candidates and native evidence."""
import collections
import json
from pathlib import Path
import sys

import common as c
from capture import write
from gates.vmc import protocol as dg
from verify_candidates import files,make_command,qualification


def review_collection(root=c.ROOT,*,validate=None):
    _,tasks,order=(validate or (lambda:c.validate_package(root)))()
    if validate is None:
        env=c.read(root/'collection-environment.json');auth=c.read(root/'authorization.json')
        submission=c.read(root/'submissions/collect.json')
        c.require(env['job_id']==submission['job_id'] and env['cpus']==1 and env['runtime_sha256']==c.sha(root/'runtime-freeze.json'),'Collector provenance differs')
        c.require(auth['authorized'] is True and auth['max_calls']==16 and auth['retries'] is False and auth['reassign_unused'] is False,'Historical authorization differs')
        c.require(auth['runtime_sha256']==env['runtime_sha256'] and auth['proposal_sha256']==c.FREEZE_SHA,'Approval pins differ')
    out=root/'model-001';ledger=c.read(out/'requests/ledger.json');rows=c.read(out/'results.json')
    summary=c.read(out/'summary.json');reservations=ledger['reservations']
    if validate is None:c.require(ledger['deadline']==auth['expires_at_epoch'],'Dispatch deadline differs')
    c.require(ledger['limit']==16 and ledger['closed'] is True and len(reservations)<=16,'Open/excess ledger')
    c.require(len(rows)<=16 and [r['slot'] for r in rows]==list(range(1,len(rows)+1)),'Trial prefix differs')
    ids=set();admitted=[];tokens=collections.Counter();completed=0
    for i,res in enumerate(reservations):
        slot=order[i];d=out/('slot-%02d'%slot['slot'])
        c.require(res['sequence']==i+1 and res['task_id']==slot['task'] and res['attempt_id']==d.name,'Reservation identity differs')
        payload=c.read(root/'frozen-001'/slot['payload'])
        c.require(res['prompt']==payload and c.read(d/'request.json')==payload and c.read(d/'slot.json')==slot,'Frozen request differs')
        c.require(res['status'] in ('COMPLETED','AMBIGUOUS_OR_UNSAVED','RESERVED'),'Unknown reservation state')
        c.require(res['reserved_at_epoch']<ledger['deadline'],'Reservation after deadline')
        if 'dispatch_started_at_epoch' in res:c.require(res['dispatch_started_at_epoch']<ledger['deadline'],'Dispatch after deadline')
        if res['status']!='COMPLETED':
            c.require(i==len(reservations)-1 and not (out/'requests'/('response-%03d.json'%(i+1))).exists(),'Evidence after unresolved request')
            continue
        completed+=1
        response=c.read(out/'requests'/('response-%03d.json'%(i+1)))
        c.require(response==c.read(d/'response.json'),'Response copies differ')
        row=rows[i];c.require(c.read(d/'result.json')==row,'Row differs')
        for k,v in slot.items():c.require(row[k]==v,'Row slot differs')
        if row['outcome']=='RESPONSE_METADATA_STOP':
            c.require(i==len(reservations)-1,'Metadata failure continued');continue
        c.check_response_metadata(response,ids)
        # The exact native response must justify all extracted transport fields.
        native=response['raw_response'];blocks=native['output']['message']['content']
        c.require(response['content']==blocks and response['text']==''.join(b['text'] for b in blocks if 'text' in b),'Text extraction differs')
        c.require(response['usage']==native['usage'] and response['stop_reason']==native['stopReason'],'Provider fields differ')
        c.require(response['request_id']==native['ResponseMetadata']['RequestId'] and response['retry_attempts']==native['ResponseMetadata']['RetryAttempts'],'Provider metadata differs')
        extraction,candidate=c.classify_response(response,slot['task'],root)
        c.require(c.read(d/'extraction.json')==extraction and row['outcome']==extraction['outcome'],'Guard replay differs')
        c.require(row['request_id']==response['request_id'] and row['usage']==response['usage'] and row['retry_attempts']==0 and row['stop_reason']==response['stop_reason'],'Result metadata differs')
        tokens.update(response['usage'])
        if candidate is None:
            c.require(not (d/'candidate.txt').exists() and row['candidate_sha256'] is None,'Rejected candidate exists')
        else:
            c.require((d/'candidate.txt').read_bytes()==candidate and row['candidate_sha256']==c.sha(d/'candidate.txt'),'Candidate replay differs')
            admitted.append(dict(slot=slot['slot'],task=slot['task'],arm=slot['arm'],candidate_sha256=row['candidate_sha256']))
    c.require(summary['reserved']==len(reservations) and summary['completed_responses']==completed,'Ledger summary differs')
    c.require(summary['dispatch_started']==sum('dispatch_started_at_epoch' in r for r in reservations),'Dispatch count differs')
    c.require(summary['ambiguous_or_unsaved']==sum(r['status']=='AMBIGUOUS_OR_UNSAVED' for r in reservations),'Ambiguity count differs')
    complete=len(rows)==16 and completed==16 and all(r['outcome'] in ('ADMITTED','OUTPUT_REJECTED','OUTPUT_TRUNCATED') for r in rows)
    c.require(summary['status']==('COLLECTION_COMPLETE' if complete else 'COLLECTION_STOPPED'),'Completion claim differs')
    c.require(summary['admitted']==len(admitted) and summary['verifier_invocations']==0 and summary['proposal_sha256']==c.FREEZE_SHA,'Scope/count differs')
    c.require(summary['result_rows']==len(rows) and summary['unused_calls_not_reassigned']==16-len(reservations),'Row/remaining count differs')
    pins={'model-001/'+n:h for n,h in files(out).items()}
    return dict(status='COLLECTION_REVIEW_PASSED',collection_complete=complete,reserved=len(reservations),completed_responses=completed,
                unique_request_ids=len(ids),sdk_retries=None if any(r['outcome']=='RESPONSE_METADATA_STOP' for r in rows) else 0,
                tokens=dict(tokens),tokens_cover_validated_metadata_only=True,admitted=admitted,collection_files=pins,
                proposal_sha256=c.FREEZE_SHA,runtime_sha256=c.sha(root/'runtime-freeze.json'),
                unused_slots_not_reassigned=16-len(reservations),unresolved_request_has_no_proof_score=True)


def review_verification(project,root=c.ROOT):
    _,tasks,_=c.validate_package(root);gate=c.read(root/'verification-gate.json')
    c.check_pins(root,gate['collection_files'])
    c.require(gate['proposal_sha256']==c.FREEZE_SHA and gate['runtime_sha256']==c.sha(root/'runtime-freeze.json'),'Gate pins differ')
    entries=[e for e in gate['admitted'] if tasks[e['task']]['project']==project]
    out=root/('verification-'+project+'-001');environment=c.read(out/'environment.json')
    c.require(environment['job_id']==c.read(root/'submissions'/(project+'.json'))['job_id'],'Verifier job provenance differs')
    c.require(environment['verification_gate_sha256']==c.sha(root/'verification-gate.json') and environment['runtime_sha256']==c.sha(root/'runtime-freeze.json'),'Worker gate/runtime differs')
    c.require(environment['cpus']==c.STAGES[project]['cpus'] and environment['model_calls']==0,'Worker resources/provenance differ')
    complete=c.read(out/'complete.json');c.require(complete['expected_candidates']==len(entries),'Missing candidates')
    c.require({p.name for p in out.iterdir() if p.is_dir()}=={'slot-%02d'%e['slot'] for e in entries},'Unexpected/missing trial folders')
    projects={p['id']:p for p in c.read(qualification(root)/'source-manifest.json')};rows=[]
    for entry in entries:
        tid=entry['task'];slot_id='slot-%02d'%entry['slot'];d=out/slot_id;task=tasks[tid]
        native=c.read(d/'record.json');profile=c.read(d/'profile.json');bound=c.read(d/'bound-record.json')
        raw={n:(d/n).read_bytes() for n in bound['raw_sha256']}
        dg.check_record(bound,profile,environment['job_id']+':'+slot_id,raw)
        expected={**projects[project]['files'],task['file']:entry['candidate_sha256']}
        command,logical,_,required,base=make_command(project,slot_id,root/'work'/project/slot_id,root)
        remote_root=environment['execution_root'];remote_outputs=str(Path(remote_root).parent.parent)
        command=[a.replace(str(root.parent.parent),remote_outputs) for a in command]
        c.require(native['command']==command and native['cwd']==remote_root,'Native command differs')
        c.require(native['model_calls']==0 and native['attempts']==1 and native['exit_code']==bound['exit_code'] and native['elapsed_seconds']==bound['elapsed_seconds'],'Native process differs')
        c.require(native['artifacts']=={n:dg.sha(raw[n]) for n in ['stdout.txt','stderr.txt','resources.txt']},'Native log hashes differ')
        expected_profile=dict(task=task,slot=entry,source_sha256=expected,logical_command=logical,toolchain=base['toolchain'],required=required)
        c.require(profile==expected_profile,'Expected source/scope profile differs')
        observation=c.verification_observation(project,native,raw,base)
        c.require(c.read(d/'observation.json')==observation,'Observation replay differs')
        if observation['qualified_scope_pass']:
            acceptance=c.read(d/'accepted.json')
            c.require(acceptance==dict(slot=entry['slot'],task=tid,candidate_sha256=entry['candidate_sha256'],protected_source_sha256=expected,
                                      observation_sha256=c.sha(d/'observation.json'),acceptance='qualified_declared_scope',live_repository_promoted=False),'Acceptance differs')
        else:c.require(not (d/'accepted.json').exists(),'Failed source accepted')
        row=dict(slot=entry['slot'],task=tid,category=observation['category'],qualified_scope_pass=observation['qualified_scope_pass'],
                 strict_zero_warning_pass=observation['strict_zero_warning_pass'],coverage_complete=observation['coverage_complete'],
                 warnings_match_upstream=observation['warnings_match_upstream'],exit_code=native['exit_code'],elapsed_seconds=native['elapsed_seconds'])
        rows.append(row)
    c.require(complete==dict(project=project,model_calls=0,results=rows,expected_candidates=len(entries)),'Worker summary differs')
    return dict(status='VERIFICATION_REVIEW_PASSED',project=project,results=rows,qualified_passes=sum(r['qualified_scope_pass'] for r in rows),
                candidates=len(rows),raw_files=files(out),no_new_model_calls=True)


def main():
    action=sys.argv[1]
    if action=='collection':
        report=review_collection();write(c.ROOT/'collection-review-001.json',report)
        write(c.ROOT/'verification-gate.json',{k:report[k] for k in ['proposal_sha256','runtime_sha256','collection_files','admitted']})
        print(json.dumps({k:v for k,v in report.items() if k not in ('collection_files','admitted')},indent=2))
    else:
        c.require(action in ('dafny-vmc','vest'),'Choose collection or repository')
        report=review_verification(action);write(c.ROOT/('review-'+action+'-001.json'),report)
        print(json.dumps({k:v for k,v in report.items() if k!='raw_files'},indent=2))


if __name__=='__main__':main()
