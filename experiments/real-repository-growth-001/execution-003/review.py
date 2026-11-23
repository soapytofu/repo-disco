"""Replay a saved growth run without provider, credential or verifier access."""
import argparse
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace
import json

import runtime as r
import run_pilot as host


def native_binding(api, value):
    value = dict(value)
    value['artifact_sha256'] = tuple(tuple(x) for x in value['artifact_sha256'])
    return api.NativeBinding(**value)


def review_run(repo, out, *, allow_synthetic=False, expected_package=None):
    from native_host import audit_candidate_native, classify
    repo, out = Path(repo).resolve(), Path(out)
    run = r.read(out / 'run.json')
    synthetic = run.get('synthetic')
    r.require(type(synthetic) is bool and (not synthetic or allow_synthetic), 'Synthetic run is not model evidence')
    r.require(expected_package is None or synthetic and allow_synthetic, 'Only tests may supply an unfrozen package')
    package = expected_package or r.validate_package(repo)
    r.require(run['package'] == package, 'Run package does not match current frozen inputs')
    if not synthetic:
        auth = r.validate_authorization(out / 'authorization.json', repo, now=run['started_at_epoch'])
        r.require(auth['expires_at_epoch'] == run['deadline'], 'Run deadline differs from authorization')
        claim=r.read(out/'execution.claim.json')
        r.require(r.sha((out/'authorization.json').read_bytes())==run['authorization_sha256']==claim['authorization_sha256'] and
                  r.sha((out/'execution.claim.json').read_bytes())==run['execution_claim_sha256'] and
                  claim['execution_id']==r.EXECUTION_ID and claim['runtime_sha256']==package['runtime_sha256'] and
                  claim['output']==auth['authorized_runtime_root']+'/model-001' and claim['no_resume'] is True,
                  'Execution claim is not bound to the exact authorization and output')
        r.require(r.read(out/'environment.json')['job_id']==claim['job_id'], 'Execution job provenance differs')
    manifest = r.read(out / 'archive-manifest.json')
    actual = {p.relative_to(out).as_posix(): r.sha(p.read_bytes()) for p in r.archive_files(out)}
    r.require(actual == manifest, 'Missing, changed or additional run evidence')
    renderer, api = r.load_context(repo)
    ledger = r.read(out / 'requests/ledger.json')
    rows = r.read(out / 'results.json')
    summary = r.read(out / 'summary.json')
    reservations = ledger['reservations']
    r.require(ledger['closed'] is True and ledger['limit'] == r.LIMIT and ledger['deadline'] == run['deadline'] and
              len(reservations) <= r.LIMIT, 'Open, overbudget or contradictory ledger')
    r.require([x['sequence'] for x in reservations] == list(range(1, len(reservations) + 1)), 'Reservation sequence differs')
    order = package['order']
    positions = {x['slot_id']: x for x in order}
    r.require(len({x['attempt_id'] for x in reservations}) == len(reservations), 'Retried/reassigned slot')
    r.require(all(x['attempt_id'] in positions and x['task_id'] == positions[x['attempt_id']]['stage_id'] for x in reservations),
              'Request outside frozen plan')
    ordinals = [positions[x['attempt_id']]['ordinal'] for x in reservations]
    r.require(ordinals == sorted(ordinals), 'Dispatch order changed')
    r.require(len({x['slot_id'] for x in rows}) == len(rows) and
              [x['slot_id'] for x in rows] == [x['slot_id'] for x in order[:len(rows)]], 'Result rows are not the fixed prefix')
    reservation_audit=[]
    response_ids=set()
    scored={x['slot_id'] for x in rows}
    for number,entry in enumerate(reservations):
        folder=out/entry['attempt_id']
        r.require(entry['prompt']==r.read(folder/'request.json'),'Reserved prompt differs from archived payload')
        status=entry['status']
        r.require(status in ('RESERVED','COMPLETED','AMBIGUOUS_OR_UNSAVED'),'Unknown ledger status')
        unscored=entry['attempt_id'] not in scored
        if status!='COMPLETED':
            r.require(unscored and number==len(reservations)-1 and summary['fatal'] is not None,
                      'Uncompleted reservation was scored or followed by another dispatch')
            reservation_audit.append(dict(slot_id=entry['attempt_id'],status=status,proof_score=None))
            continue
        raw_path=out/'requests'/('response-%03d.json'%entry['sequence'])
        r.require(raw_path.is_file(),'Completed ledger reservation has no full saved response')
        returned=r.read(raw_path)
        if (folder/'response.json').exists():
            r.require(r.read(folder/'response.json')==returned,'Slot response differs from canonical ledger response')
        else:
            r.require(unscored and summary['fatal'] is not None,'Scored response is missing')
        try:
            r.check_response(returned,response_ids)
        except (ValueError,TypeError,KeyError) as error:
            r.require(unscored and number==len(reservations)-1 and summary['fatal'] is not None,
                      'Invalid provider metadata was scored or followed by another dispatch')
            reservation_audit.append(dict(slot_id=entry['attempt_id'],status=status,
                metadata_valid=False,error_type=type(error).__name__,proof_score=None))
        else:
            reservation_audit.append(dict(slot_id=entry['attempt_id'],status=status,metadata_valid=True,
                                         scored=not unscored,request_id=returned['request_id']))
    gate = SimpleNamespace(directory=out/'requests', state=ledger)
    originals, parents, seen, audited, native_counts, expected_heads = {}, {}, set(), [], [], {}
    lookup = {x['attempt_id']: x for x in reservations}
    for row in rows:
        slot = positions[row['slot_id']]
        folder = out / slot['slot_id']
        r.require(r.read(folder/'slot.json') == slot and r.read(folder/'result.json') == row, 'Per-slot result drift')
        r.require(all(row.get(k) == v for k, v in slot.items()) and row.get('synthetic') is synthetic, 'Slot metadata drift')
        if row['outcome'] == 'BLOCKED_PARENT':
            r.require(slot['stage'] == 2 and slot['lineage_id'] not in parents and slot['slot_id'] not in lookup and
                      not (folder/'request.json').exists(), 'Blocked child was dispatched or had an accepted parent')
            audited.append(dict(slot_id=slot['slot_id'], outcome='BLOCKED_PARENT'))
            continue
        entry = lookup.get(slot['slot_id'])
        r.require(entry and entry['status'] == 'COMPLETED' and 'dispatch_started_at_epoch' in entry,
                  'Scored slot has no completed reservation')
        response = r.read(folder/'response.json')
        r.check_response(response, seen)
        r.require(row.get('request_id')==response['request_id'] and row.get('usage')==response['usage'] and
                  type(row.get('retry_attempts')) is int and row['retry_attempts']==response['retry_attempts'],
                  'Scored row provider identity or usage differs from the actual response')
        original = originals.setdefault(slot['project'], host.original_sources(repo, slot['project'], api))
        kwargs = dict(chain_id=slot['lineage_id'])
        if slot['stage'] == 1:
            source_parent = original
            rendered = renderer.render_stage1(slot['slot_id'])
        else:
            r.require(slot['lineage_id'] in parents, 'Child has no accepted parent from this run')
            parent = parents[slot['lineage_id']]
            # Review the immutable stage-one receipt, independent of the final head now possibly at stage two.
            source_parent = host.load_sources(parent.folder, original, api)
            evidence = host.load_evidence(parent, api)
            current = host.provenance(parent.folder, parent.slot, gate, source_parent, api,
                                      run['run_id'], package['runtime_sha256'])
            r.require(current == parent.provenance and
                      api.b.read_json(evidence['accepted.json'])['host_request_provenance'] == current,
                      'Parent is not the current run completed request')
            kwargs.update(parent_binding=parent.binding, parent_artifacts=evidence, allow_synthetic=synthetic)
            rendered = (renderer.render_synthetic_stage2_for_tests(slot['slot_id'], source_parent,
                        parent.binding, evidence, acknowledge_synthetic=True) if synthetic else
                        renderer.render_stage2(slot['slot_id'], source_parent, parent.binding, evidence))
        r.require(r.read(folder/'request.json') == rendered['payload'] == entry['prompt'] and
                  r.read(folder/'rendering.json') == rendered['rendering'], 'Payload or actual-parent rendering drift')
        if row['outcome'] == 'OUTPUT_TRUNCATED':
            r.require(response['stop_reason'] == 'max_tokens' and not (folder/'native').exists(), 'Truncation changed')
        elif row['outcome'] == 'GUARD_REJECTED':
            try:
                host.parse_body(response, slot['stage_id'], api)
            except (ValueError, TypeError, KeyError, RecursionError) as error:
                r.require(row['rejection_type'] == type(error).__name__ and row['rejection_message'] == str(error)[:512],
                          'Guard rejection differs')
            else:
                raise ValueError('Claimed guard rejection now admits')
            r.require(not (folder/'native').exists(), 'Guard-rejected candidate was verified')
        else:
            body, envelope = host.parse_body(response, slot['stage_id'], api)
            sources, guard = api.b.reconstruct(slot['stage_id'], body, source_parent, **kwargs)
            guard['envelope'] = envelope
            r.require(sources == host.load_sources(folder, original, api) and r.read(folder/'guard.json') == guard,
                      'Candidate is not the guarded saved response')
            request_origin = host.provenance(folder, slot, gate, sources, api, run['run_id'], package['runtime_sha256'])
            r.require(r.read(folder/'request-provenance.json') == request_origin, 'Request origin drift')
            if row.get('native_evidence_incomplete'):
                r.require(row['native_terminal'] is True and row['qualified_pass'] is False and
                          summary['fatal'] is not None and row == rows[-1] and
                          not (folder/'evidence/accepted.json').exists(), 'Incomplete native result was promoted')
                audited.append(dict(slot_id=slot['slot_id'], outcome=row['outcome'], proof_score=None))
                continue
            binding = native_binding(api, r.read(folder/'native-binding.json'))
            artifacts = {name: r.pinned_path(folder/'evidence', name).read_bytes() for name, _ in binding.artifact_sha256}
            r.require(binding.run_id == run['run_id']+':'+slot['slot_id'] and binding.stage == slot['stage'] and
                      binding.project == slot['project'] and binding.origin == ('synthetic-offline' if synthetic else 'model-candidate'),
                      'Native invocation identity differs')
            extraction = audit_candidate_native(binding, artifacts, sources, repo, allow_synthetic=synthetic)
            r.require(api.b.canonical(extraction) == (folder/'evidence/native-units.json').read_bytes(), 'Native extraction differs')
            category, terminal = classify(extraction)
            r.require(row['qualified_pass'] == extraction['qualified_pass'] and row['native_terminal'] == terminal and
                      row['outcome'] == ('ACCEPTED' if extraction['qualified_pass'] else category), 'Native classification differs')
            if row['outcome'] == 'ACCEPTED':
                if slot['stage'] == 1:
                    value = r.read(folder/'accepted-parent-binding.json')
                    value['native'] = native_binding(api, value['native'])
                    pb = api.AcceptedParentBinding(**value)
                    r.require(pb.native == binding, 'Accepted native binding drift')
                    head = dict(status='accepted', stage=1, slot_id=slot['slot_id'], lineage_id=slot['lineage_id'],
                                source_revision_sha256=binding.source_revision_sha256,
                                receipt_sha256=pb.receipt_sha256, synthetic=synthetic)
                    parent = host.Parent(slot, folder, pb, request_origin, head)
                    evidence = host.load_evidence(parent, api)
                    r.require(api.b.read_json(evidence['accepted.json'])['host_request_provenance'] == request_origin,
                              'Stage-one acceptance lost authentic request link')
                    api.validate_accepted_parent(api.STAGES[slot['project']][1], slot['lineage_id'], sources,
                                                 pb, evidence, allow_synthetic=synthetic, repo=repo)
                    parents[slot['lineage_id']] = parent
                    expected_heads[slot['lineage_id']] = head
                else:
                    receipt = r.read(folder/'accepted-stage-two.json')
                    r.require(receipt['schema']=='repodisco-growth-stage-two-acceptance-v1' and
                              receipt['status']=='accepted' and receipt['synthetic'] is synthetic and
                              receipt['slot_id']==slot['slot_id'] and receipt['lineage_id']==slot['lineage_id'] and
                              receipt['host_request_provenance'] == request_origin and
                              receipt['accepted_parent_binding_sha256'] == r.sha(r.canonical(asdict(parents[slot['lineage_id']].binding))) and
                              receipt['native_binding_sha256'] == r.sha(r.canonical(asdict(binding))) and
                              receipt['native_extraction_sha256'] == r.sha(api.b.canonical(extraction)) and
                              receipt['source_revision_sha256'] == binding.source_revision_sha256,
                              'Stage-two acceptance lost native/parent/request link')
                    expected_heads[slot['lineage_id']]=dict(status='accepted',stage=2,slot_id=slot['slot_id'],
                        lineage_id=slot['lineage_id'],synthetic=synthetic,
                        source_revision_sha256=binding.source_revision_sha256,
                        receipt_sha256=r.sha((folder/'accepted-stage-two.json').read_bytes()))
            native_counts.append(dict(slot_id=slot['slot_id'], qualified_pass=extraction['qualified_pass']))
        audited.append(dict(slot_id=slot['slot_id'], outcome=row['outcome']))
    complete = summary['status'] in ('COMPLETE', 'SYNTHETIC_COMPLETE')
    head_root=out/'accepted-heads'
    if head_root.exists():
        r.require(head_root.is_dir() and not head_root.is_symlink(), 'Invalid accepted-heads directory')
        head_files=list(head_root.iterdir())
    else:
        # Files-only evidence transfer omits an empty directory. Absence is
        # equivalent to empty only when no accepted head is expected at all.
        r.require(not expected_heads, 'Missing required accepted-heads directory')
        head_files=[]
    r.require({p.name for p in head_files}=={name+'.json' for name in expected_heads},'Unexpected accepted head')
    for name,expected in expected_heads.items():
        r.require(r.read(out/'accepted-heads'/(name+'.json'))==expected,'Promoted revision differs from actual last accepted stage')
    for entry in reservations:
        slot=positions[entry['attempt_id']]
        if slot['stage']==2:
            r.require(slot['lineage_id'] in parents and parents[slot['lineage_id']].slot['slot_id']==slot['parent_slot'],
                      'A child request was made without its exact accepted parent')
    r.require(complete == (summary['fatal'] is None and len(rows) == r.LIMIT), 'False completion claim')
    if complete:
        r.require(len(reservations) == len(rows)-sum(x['outcome']=='BLOCKED_PARENT' for x in rows) and
                  all(x['status']=='COMPLETED' for x in reservations), 'Completed run has missing responses')
    r.require(summary['transport_reservations']==len(reservations) and
              summary['completed_responses']==sum(x['status']=='COMPLETED' for x in reservations) and
              summary['accepted_stages']==sum(x['outcome']=='ACCEPTED' for x in rows) and
              summary['completed_lineages']==sum(x['outcome']=='ACCEPTED' and x['stage']==2 for x in rows),
              'Summary accounting differs')
    r.require(summary['ambiguous_or_unsaved']==sum(x['status']=='AMBIGUOUS_OR_UNSAVED' for x in reservations) and
              summary['unused_capacity_never_reassigned']==r.LIMIT-len(reservations) and
              summary['dispatched_slots']==[x['attempt_id'] for x in reservations if 'dispatch_started_at_epoch' in x] and
              summary['blocked_children']==[x['slot_id'] for x in rows if x['outcome']=='BLOCKED_PARENT'] and
              summary['unprocessed_slots']==[x['slot_id'] for x in order if x['slot_id'] not in scored],
              'Unscored, blocked or undispatched accounting differs')
    return dict(status='SYNTHETIC_REPLAY_PASSED' if synthetic else 'RUN_EVIDENCE_REPLAY_PASSED',
                synthetic=synthetic, experiment_complete=complete, reserved=len(reservations),
                completed_responses=summary['completed_responses'], reviewed_rows=audited,
                reservation_audit=reservation_audit,
                accepted_stages=summary['accepted_stages'], completed_lineages=summary['completed_lineages'],
                model_calls_made_by_review=0, native_calls_made_by_review=0,
                stopped_run_has_no_complete_pilot_score=not complete)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(review_run(args.repo,args.output),indent=2))
