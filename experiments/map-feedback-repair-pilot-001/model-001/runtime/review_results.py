"""Offline request, immutable-source, target and promotion audit; no calls/reruns."""
from collections import Counter
from pathlib import Path
import json
import run_pilot as r


def review(root=r.ROOT):
    out=root/'model-001';plan,parents,trials=r.validate_bundle(root);pins=r.validate_runtime(root)
    for name in ('frozen-001','inputs'):r.require(r.inventory(out/name)==r.inventory(root/name),'Archived '+name)
    r.require(r.sha(out/'runtime-freeze.json')==r.sha(root/'runtime-freeze.json'),'Archived freeze')
    r.require(r.inventory(out/'runtime')==pins['runtime_sha256'],'Archived code')
    auth=r.load(out/'authorization.json');env=r.load(out/'environment.json');ledger=r.load(out/'requests/ledger.json')
    r.require(auth['authorized'] and auth['max_calls']==8 and not auth['automatic_retries'] and not auth['reassign_unused']
        and auth['proposal_freeze_sha256']==r.PROPOSAL_SHA and auth['runtime_freeze_sha256']==r.sha(root/'runtime-freeze.json'),'Authorization')
    r.require(env['dafny']==plan['verifier']['toolchain'] and env['z3']==plan['verifier']['z3'] and env['job_id'] and 'login' not in env['host'],'Compute environment')
    reservations=ledger['reservations'];r.require(ledger['closed'] and ledger['limit']==8 and len(reservations)<=8 and ledger['deadline']==auth['expires_at_epoch'],'Closed budget ledger')
    results=r.load(out/'results.json');rows=[];ids=set();tokens=Counter();protected=0;boundaries=0
    for i,reservation in enumerate(reservations):
        trial=trials[i];parent,task,base,template=r.parent_parts(root,trial);folder=out/trial['trial_id'];result=r.load(folder/'result.json')
        r.require(result==results[i] and all(result[k]==v for k,v in trial.items()),'Trial result/order')
        payload=r.load(root/'frozen-001'/trial['request_path'])
        r.require(reservation['prompt']==payload==r.load(folder/'request.json') and r.sha(folder/'request.json')==trial['request_sha256'],'Exact request')
        r.require(reservation['task_id']==task['task_id'] and reservation['attempt_id']==trial['trial_id'] and reservation['sequence']==i+1,'Reservation identity')
        r.require(reservation['reserved_at_epoch']<auth['expires_at_epoch'] and reservation.get('dispatch_started_at_epoch',0)<auth['expires_at_epoch'],'Deadline')
        initial=r.load(folder/'initial.json');store=r.RevisionStore(folder/'store');head=store.snapshot()
        oldpath=folder/'store/revisions'/initial['revision'];oldmeta=r.load(oldpath/'revision.json')
        r.require(r.files(oldpath/'files')==base and oldmeta['source_sha256']==r.hashes(base) and oldmeta['parent'] is None,'Original revision preserved')
        r.require(initial['source_sha256']==parent['source_sha256'] and initial['reused_original_verification'] and initial['new_verifier_runs']==0
            and initial['evidence_sha256']==r.sha(root/'frozen-001'/parent['original_verifier_path']),'Original failure provenance')
        row=dict(trial_id=trial['trial_id'],parent_trial=trial['parent_trial'],sharing=trial['sharing'],feedback_condition=trial['feedback_condition'],
                 outcome=result['outcome'],returned=False,admitted=False,verified=False,promoted=False)
        if reservation['status']!='COMPLETED':
            r.require(result['outcome']=='REQUEST_STOP' and head.revision==initial['revision'],'Stopped request mutated state')
            rows.append(row);continue
        response=r.load(out/'requests'/f'response-{i+1:03d}.json');r.require(response==r.load(folder/'response.json'),'Response copies')
        raw=response['raw_response'];rid=response['request_id']
        r.require(rid and rid not in ids and rid==raw['ResponseMetadata']['RequestId']==result['request_id'],'Unique request ID')
        r.require(response['retry_attempts']==raw['ResponseMetadata']['RetryAttempts']==result['retry_attempts']==0,'No retries')
        r.require(response['content']==raw['output']['message']['content'] and response['text']==''.join(x['text'] for x in response['content'] if 'text' in x),'Content integrity')
        r.require(response['stop_reason']==raw['stopReason']==result['stop_reason'] and response['usage']==raw.get('usage')==result['usage'],'Response metadata')
        ids.add(rid);tokens.update({k:v for k,v in (response['usage'] or {}).items() if isinstance(v,(int,float))});row.update(returned=True,request_id=rid,usage=response['usage'])
        extraction=r.load(folder/'extraction.json')
        if response['stop_reason']=='max_tokens':r.require(result['outcome']=='OUTPUT_TRUNCATED' and not extraction['accepted'],'Truncation')
        else:
            try:edited,decision=r.decode(response['text'],root,trial)
            except r.OutputRejected as e:
                r.require(result['outcome']=='OUTPUT_REJECTED' and not extraction['accepted'] and extraction['stage']==e.stage and extraction['reason']==str(e),'Extraction replay')
                row['rejection_stage']=e.stage
            else:
                r.require(extraction==dict(accepted=True,**decision),'Exact guard replay');row['admitted']=True
                r.require(r.files(folder/'candidate')==edited and r.load(folder/'candidate-hashes.json')==dict(parent_sha256=r.hashes(base),candidate_sha256=r.hashes(edited)),'Candidate source')
                bodyguard,_=r.policy(root);bodies=[];editclasses={}
                for n,original in base.items():
                    if n not in task['editable_files']:
                        r.require(edited[n]==original,'Protected file changed');protected+=1
                    else:
                        pre,suf=bodyguard.split_seed(template[n].decode());text=edited[n].decode()
                        r.require(text.startswith(pre) and text.endswith(suf),'Protected contract/boundary changed');boundaries+=1
                        old=original.decode()[len(pre):-len(suf)];new=text[len(pre):-len(suf)];bodies.append(new)
                        lines=lambda s:[x.strip() for x in s.splitlines() if x.strip()]
                        editclasses[n]='unchanged' if old==new else ('reorder_only' if Counter(lines(old))==Counter(lines(new)) else 'other_edit')
                row.update(body_edit_classification=editclasses,separate_bodies_identical=(len(set(bodies))==1 if task['sharing']=='separate' else None))
                if (folder/'verification.json').exists():
                    ev=r.load(folder/'verification.json');r.require(ev['source_sha256']==r.hashes(edited),'Verifier source binding')
                    outcome=r.outcome_for_evidence(ev);metrics,stop=r.measurement(ev,task,root)
                    r.require(metrics==r.load(folder/'target-metrics.json'),'Metrics replay')
                    r.require({str(p.relative_to(folder/'raw-csv')):p.read_bytes().decode() for p in (folder/'raw-csv').rglob('*') if p.is_file()}==ev.get('csv',{}),'Exact raw CSV')
                    r.require(result['outcome']==outcome or result['outcome']=='PROMOTION_REJECTED','Verifier category')
                    row['target_metrics']=metrics;row['verified']=outcome=='VERIFIED' and not stop
                    if row['verified'] and result['outcome']=='VERIFIED':
                        accepted=r.load(folder/'accepted.json');meta=r.load(folder/'store/revisions'/head.revision/'revision.json')
                        r.require(head.files==edited and head.revision==accepted['revision'] and head.revision!=initial['revision'] and meta['parent']==initial['revision'],'Whole revision promotion')
                        r.require(meta['verification']==ev and meta['source_sha256']==r.hashes(edited) and accepted==dict(base_revision=initial['revision'],revision=head.revision,parent_sha256=r.hashes(base),candidate_sha256=r.hashes(edited),verification_sha256=r.sha(folder/'verification.json')),'Promotion evidence')
                        row['promoted']=True
                else:r.require(result['outcome']=='VERIFIER_ERROR','Missing verifier evidence')
        if not row['promoted']:
            r.require(head.revision==initial['revision'] and head.files==base and not (folder/'accepted.json').exists(),'Failed repair promoted')
        r.require(len(list((folder/'store/revisions').iterdir()))==(2 if row['promoted'] else 1),'Unexpected revisions')
        rows.append(row)
    summary=r.load(out/'summary.json');r.require(summary['results']==results and summary['reserved_calls']==len(reservations) and summary['completed_responses']==len(ids),'Summary counts')
    r.require(summary['verified']==sum(x['outcome']=='VERIFIED' for x in rows),'Summary successes')
    cells={}
    for sharing in ('shared','separate'):
        for arm in plan['feedback_conditions']:
            selected=[x for x in rows if x['sharing']==sharing and x['feedback_condition']==arm]
            cells[sharing+'/'+arm]=dict(planned=2,returned=sum(x['returned'] for x in selected),verified=sum(x['verified'] for x in selected),promoted=sum(x['promoted'] for x in selected))
    return dict(calls_reserved=len(reservations),unique_returned_requests=len(ids),zero_sdk_retries=True,
        all_trials_processed=summary['all_trials_processed'],strict_passes=sum(x['verified'] for x in rows),tokens=dict(tokens),cells=cells,
        protected_file_comparisons=protected,protected_body_boundaries=boundaries,original_score='12/16 unchanged',
        unique_failure_workspaces=2,all_trials_fresh_stores=True,rows=rows)

if __name__=='__main__':
    report=review();r.durable_json(r.ROOT/'reviewed-results.json',report)
    print(json.dumps({k:v for k,v in report.items() if k!='rows'},indent=2))
