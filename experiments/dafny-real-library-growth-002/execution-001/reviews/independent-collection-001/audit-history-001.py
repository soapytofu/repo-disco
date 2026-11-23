"""Independent offline inspection of the three saved model/native observations.

Imports only the already reviewed local pure runtime/guard/scorer. Does not run
the collection reviewer, subprocesses, verifiers, providers, SSH, or Git.
"""
import csv
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
EXEC=ROOT/'execution-001'
ARCHIVE=EXEC/'retrieved-001'
MODEL=ARCHIVE/'model-001'
sys.path.insert(0,str(EXEC))
import runtime as rt


def read(path):
    return json.loads(Path(path).read_bytes())


def snapshot(path):
    result={}
    for file in sorted(Path(path).rglob('*')):
        assert not file.is_symlink(), file
        if file.is_file():
            raw=file.read_bytes()
            result[file.relative_to(path).as_posix()]=dict(bytes=len(raw),sha256=rt.sha(raw))
    return result


transfer=read(EXEC/'transfer-001.json')
assert transfer['job_id']=='63210633'
assert len(transfer['files'])==398
assert snapshot(ARCHIVE)==transfer['files']
tar_raw=(EXEC/'transfer-001.tar.gz').read_bytes()
assert rt.sha(tar_raw)==transfer['archive_sha256'] and len(tar_raw)==transfer['compressed_bytes']
with tarfile.open(fileobj=io.BytesIO(tar_raw)) as archive:
    members=archive.getmembers()
    assert len(members)==398 and len({m.name for m in members})==398
    for member in members:
        assert member.isfile() and rt.native.safe_path(member.name)
        assert rt.sha(archive.extractfile(member).read())==transfer['files'][member.name]['sha256']

freeze=read(EXEC/'runtime-freeze.json')
runtime_sha='13f21cc5b329db74761c1b833cc2b7722a8c784c0fea5933fa64c075978ef693'
assert rt.sha((EXEC/'runtime-freeze.json').read_bytes())==runtime_sha
for name,expected in freeze['files'].items():
    assert rt.sha((ROOT/name).read_bytes())==expected
    assert (ROOT/name).read_bytes()==(ARCHIVE/'package'/name).read_bytes()
assert (MODEL/'runtime-freeze.json').read_bytes()==(EXEC/'runtime-freeze.json').read_bytes()
scope=read(ROOT/freeze['scope']);summary=read(MODEL/'summary.json');run=read(MODEL/'run.json')
ledger=read(MODEL/'requests/ledger.json');auth=read(ARCHIVE/'authorization.json')
assert auth==read(EXEC/'authorization.json')==read(MODEL/'authorization.json')
assert auth['runtime_manifest_sha256']==runtime_sha and auth['scope_sha256']==rt.sha((ROOT/freeze['scope']).read_bytes())
assert run['synthetic'] is False and run['offline'] is False
assert run['scope_sha256']==rt.sha(rt.canonical(scope))
assert run['run_id']==summary['run_id']
assert summary['status']=='TERMINAL' and summary['declared_slots']==8
assert summary['reserved']==summary['completed']==summary['native_dispatches']==summary['native_observations']==3
assert summary['ambiguous_or_unsaved']==0 and summary['unused_request_capacity']==5
assert summary['accepted_stages']==1 and summary['fatal']==read(MODEL/'fatal.json')
assert summary['fatal']==dict(error_type='TerminalNativeError',slot_id='slot-03',native_category='FRONTEND_RESOLUTION_FAILURE')
assert ledger['closed'] is True and ledger['closed_reason']=='terminal' and ledger['limit']==8
assert len(ledger['reservations'])==3 and all(r['status']=='COMPLETED' for r in ledger['reservations'])
assert {p.name for p in (MODEL/'slots').iterdir()}=={'slot-01','slot-02','slot-03'}
assert {p.name for p in (MODEL/'requests').glob('response-*.json')}=={'response-001.json','response-002.json','response-003.json'}
assert not list(MODEL.rglob('parent-receipt.json'))
assert (ARCHIVE/'canonical-allocation-claim.json').read_bytes()==(MODEL/'allocation-claim.json').read_bytes()
assert (ARCHIVE/'canonical-budget-snapshot.json').read_bytes()==(MODEL/'budget-snapshot.json').read_bytes()==(EXEC/'budget-snapshot.json').read_bytes()
claim=read(ARCHIVE/'canonical-allocation-claim.json')
assert claim['state']=='CONSUMED_NO_RESUME' and claim['authorization_sha256']==rt.sha((EXEC/'authorization.json').read_bytes())

ids=set();nonces=set();outcomes=[];tokens=dict(inputTokens=0,outputTokens=0,totalTokens=0)
expected_categories=['PROOF_FAILURE','VERIFIED','FRONTEND_RESOLUTION_FAILURE']
expected_counts=[(58,1,0),(81,0,0),(0,0,1)]
for index in range(1,4):
    slot=scope['slots'][index-1];folder=MODEL/'slots'/slot['id'];stage=scope['projects'][slot['project']]['stages']['1']
    reservation=ledger['reservations'][index-1];response=read(MODEL/'requests'/f'response-{index:03d}.json')
    assert reservation['sequence']==index and reservation['task_id']==slot['id']
    assert reservation['attempt_id']==run['run_id']+':'+slot['id']
    assert auth['created_at_epoch']<=reservation['reserved_at_epoch']<=reservation['dispatch_started_at_epoch']<auth['expires_at_epoch']
    raw_response=response['raw_response'];metadata=raw_response['ResponseMetadata']
    assert metadata['RequestId']==response['request_id'] and response['request_id'] not in ids
    assert metadata['RetryAttempts']==response['retry_attempts']==0 and metadata['HTTPStatusCode']==200
    ids.add(response['request_id'])
    blocks=raw_response['output']['message']['content']
    assert raw_response['output']['message']['role']=='assistant'
    assert response['content']==blocks and response['text']==''.join(b['text'] for b in blocks if 'text' in b)
    assert response['usage']==raw_response['usage'] and response['stop_reason']==raw_response['stopReason']=='end_turn'
    assert response['usage']['inputTokens']+response['usage']['outputTokens']==response['usage']['totalTokens']
    for key in tokens: tokens[key]+=response['usage'][key]
    prompt=read(folder/'prompt.json');payload=read(ROOT/stage['exact_payload_path'])
    assert reservation['prompt']==prompt['payload']==payload
    assert prompt['parent_audit'] is None and prompt['dispatch_eligible'] is False
    assert prompt['payload_sha256']==rt.sha(rt.canonical(payload))
    binding=dict(request_sequence=index,request_id=response['request_id'],response_sha256=rt.sha(rt.canonical(response)))
    assert read(folder/'response-binding.json')==binding
    body,envelope=rt.parse_body_receipt(response['text'])
    assert (folder/'body.txt').read_bytes()==body.encode() and read(folder/'envelope.json')==envelope
    edit_profile=read(ROOT/stage['edit_profile'])
    base={name:(ROOT/pin['path']).read_bytes() for name,pin in stage['base_sources'].items()}
    candidate,edit=rt.guard.reconstruct(edit_profile,body,base,slot['chain_id'],parent=None)
    assert edit==read(folder/'edit-review.json') and edit['acceptance_issued'] is False and edit['parent'] is None
    assert candidate==rt.source_files(folder/'candidate')==rt.source_files(folder/'native/workspace')
    assert all(candidate[name]==raw for name,raw in base.items())
    native_profile=rt.materialize_profile(read(ROOT/stage['native_profile']),candidate)
    assert native_profile==read(folder/'native-profile.json')
    raw={p.relative_to(folder/'native/raw').as_posix():p.read_bytes() for p in (folder/'native/raw').rglob('*') if p.is_file()}
    record=read(folder/'native/record.json');event=read(folder/'native-dispatch.json')
    assert event==read(folder/'native/event.json')
    assert event['run_id']==record['run_id']==run['run_id']+':'+slot['id']
    assert event['request_id']==response['request_id'] and event['request_sequence']==index
    assert event['response_sha256']==binding['response_sha256'] and event['payload_sha256']==prompt['payload_sha256']
    assert event['candidate_sha256']==rt.sha(rt.canonical(rt.native.hashes(candidate)))
    assert event['profile_sha256']==rt.sha(rt.canonical(native_profile))
    assert event['synthetic'] is False and event['nonce'] not in nonces
    nonces.add(event['nonce'])
    assert record['origin']=='model_candidate' and record['attempts']==1 and record['model_calls']==0
    assert record['source_before_sha256']==record['source_after_sha256']==rt.native.hashes(candidate)
    assert record['toolchain']==record['toolchain_after']==native_profile['toolchain']
    assert record['argv']==native_profile['command'] and record['raw_sha256']==rt.native.hashes(raw)
    assert record['host']['job_id']=='63210633' and record['host']['partition']=='test' and record['host']['cpus_per_task']==1
    assert record['timeout'] is False and 'login' not in record['host']['hostname']
    invocation=read(folder/'native/invocation-start.json')
    assert invocation['argv']==native_profile['command'] and invocation['event_sha256']==rt.sha(rt.canonical(event))
    assert invocation['wall_seconds']==stage['native_adapter']['wall_seconds']
    pins=rt.native.EvidencePins(rt.sha(rt.canonical(native_profile)),rt.sha(rt.canonical(record)),
        rt.sha(rt.canonical(rt.native.hashes(candidate))),tuple(sorted(rt.native.hashes(raw).items())),record['run_id'],record['origin'])
    replay=rt.native.review(native_profile,candidate,record,raw,pins)
    assert replay==read(folder/'native-review.json')
    assert replay['category']==expected_categories[index-1]
    assert (replay['passed_units'],replay['failed_units'],replay['warnings'])==expected_counts[index-1]
    assert replay['strict_zero_warning_success']==(index==2)
    assert record['run_id'] not in native_profile['ineligible_parent_runs']
    assert replay['raw_fingerprint_sha256'] not in native_profile['ineligible_parent_raw_fingerprints']
    csv_rows=[row for name,data in raw.items() if name.startswith('csv/') for row in csv.DictReader(io.StringIO(data.decode()))]
    labels={r['TestResult.DisplayName']:r['TestResult.Outcome'] for r in csv_rows}
    assert len(labels)==len(csv_rows)
    if index<3: assert set(labels)==set(native_profile['required_units'])
    else: assert labels=={} and len(replay['missing_units'])==60
    inherited={name:status for name,status in labels.items() if native_profile['required_units'][name]!=edit_profile['addition']['path']}
    assert all(status=='Passed' for status in inherited.values())
    row=read(folder/'outcome.json')
    assert row==summary['rows'][index-1] and all(row[k]==v for k,v in binding.items())
    assert row['accepted']==(index==2) and row['native_invoked'] is True
    outcomes.append(dict(slot_id=slot['id'],task=slot['project'],request_id=response['request_id'],
        body_sha256=rt.sha(body.encode()),protected_base_files=len(base),candidate_sha256=rt.native.hashes(candidate),
        category=replay['category'],passed_units=replay['passed_units'],failed_units=replay['failed_units'],
        warnings=replay['warnings'],native_exit=record['exit_code'],timeout=record['timeout'],
        elapsed_seconds=replay['elapsed_seconds'],resources=replay['resources'],csv_units=labels,
        inherited_passes=len(inherited),required_units=len(native_profile['required_units']),
        unlogged_definitions_not_passes=len(native_profile['unlogged_definitions']),usage=response['usage']))

versions={}
for task in ('stdlib-filter','aws-batch'):
    folder=MODEL/'native-preflight'/task;stage=scope['projects'][task]['stages']['1'];profile=read(ROOT/stage['native_profile'])
    env=read(folder/'environment.json')
    assert env['toolchain']==env['toolchain_after']==profile['toolchain']
    assert env['host']['job_id']=='63210633' and env['host']['cpus_per_task']==1
    versions[task]={}
    for name in ('dafny','solver'):
        r=read(folder/(name+'.record.json'));out=(folder/(name+'.stdout')).read_text().strip()
        assert r['exit_code']==0 and r['timeout'] is False and (folder/(name+'.stderr')).read_bytes()==b''
        assert out==profile['toolchain'][name+'_version']
        versions[task][name]=out
accounting=list(csv.DictReader(io.StringIO((ARCHIVE/'accounting.txt').read_text()),delimiter='|'))
assert [r['JobID'] for r in accounting]==['63210633','63210633.batch','63210633.extern']
assert all(r['State'] in {'FAILED','COMPLETED'} and r['AllocCPUS']=='1' and r['ElapsedRaw']=='83' for r in accounting)
assert accounting[0]['State']=='FAILED' and accounting[0]['ExitCode']=='2:0'
submission=read(ARCHIVE/'submissions/model.json')
assert submission['job_id']=='63210633' and submission['submission_attempts']==1 and submission['no_retry'] is True
assert 'PreemptMode=OFF' in submission['partition_record'] and 'State=UP' in submission['partition_record']
assert submission['authorization_sha256']==rt.sha((EXEC/'authorization.json').read_bytes())
result=dict(status='PASS_INDEPENDENT_SAVED_EVIDENCE_AUDIT',blocking_findings=[],job_id='63210633',runtime_sha256=runtime_sha,
    archive_files=398,archive_sha256=transfer['archive_sha256'],all_archive_and_tar_bytes_match=True,
    recorded_requests=3,returned_responses=3,unique_request_ids=len(ids),sdk_retries_observed=0,ambiguous_reservations=0,
    guard_admitted=3,native_invocations_observed=3,accepted_additions=1,undispatched_slots=5,
    complete_eight_trial_score=None,observed_outcomes=outcomes,tokens=tokens,versions=versions,accounting=accounting,
    stoprule_matched=True,acceptance_issued=False,model_calls_in_review=0,native_calls_in_review=0,
    inspected_files=transfer['files'],inspected_runtime_files=freeze['files'],
    audit_source_sha256=rt.sha(Path(__file__).read_bytes()))
(HERE/'audit.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
print(json.dumps({key:result[key] for key in ('status','archive_files','recorded_requests','returned_responses',
    'unique_request_ids','sdk_retries_observed','guard_admitted','native_invocations_observed',
    'accepted_additions','undispatched_slots','complete_eight_trial_score','tokens','blocking_findings')},indent=2))
