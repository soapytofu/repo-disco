"""One fresh bounded process for conditional growth; no resume or automatic retry."""
import argparse
from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import socket
import sys
import time
import uuid
from importlib.metadata import PackageNotFoundError, version

import runtime as r
from bounded_requests import RequestGate, bedrock_transport, consume_key, durable_json


def write_bytes(path, raw):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def original_sources(repo, project, api):
    _, inventory = api.b.load_assets()
    prefix = Path(repo) / 'experiments/real-repository-qualification-001/upstream' / project
    sources = {name: r.pinned_path(prefix, name).read_bytes()
               for name in inventory['projects'][project]['files']}
    api.b.check_workspace(project, 0, sources)
    return sources


def save_sources(folder, sources, original, api):
    overlay = {name: raw for name, raw in sources.items() if original.get(name) != raw}
    for name, raw in overlay.items():
        api.b.path_name(name)
        write_bytes(folder / 'source-overlay' / name, raw)
    manifest = dict(source_sha256=api.b.source_hashes(sources),
                    original_source_sha256=api.b.source_hashes(original),
                    overlay_sha256=api.b.source_hashes(overlay))
    durable_json(folder / 'source-manifest.json', manifest)
    return manifest


def load_sources(folder, original, api):
    manifest = r.read(folder / 'source-manifest.json')
    r.require(manifest['original_source_sha256'] == api.b.source_hashes(original), 'Original source binding changed')
    sources = dict(original)
    actual_paths = {p.relative_to(folder / 'source-overlay').as_posix()
                    for p in (folder / 'source-overlay').rglob('*') if p.is_file()}
    r.require(actual_paths == set(manifest['overlay_sha256']), 'Candidate overlay incomplete or extra')
    for name, digest in manifest['overlay_sha256'].items():
        raw = r.pinned_path(folder / 'source-overlay', name).read_bytes()
        r.require(r.sha(raw) == digest, 'Candidate overlay changed')
        sources[name] = raw
    r.require(api.b.source_hashes(sources) == manifest['source_sha256'], 'Candidate source map changed')
    return sources


def parse_body(response, stage_id, api):
    payload, envelope = api.b.extract_json(response['text'])
    obj = api.b.read_json(payload.encode())
    r.require(isinstance(obj, dict) and set(obj) == {'replacement'} and isinstance(obj['replacement'], str),
              'Exactly one replacement string required')
    api.b.validate_body(stage_id, obj['replacement'])
    return obj['replacement'], envelope


def provenance(folder, slot, gate, sources, api, run_id, runtime_sha):
    """Bind this process's one completed reservation to exact response and source."""
    r.require(r.read(gate.directory / 'ledger.json') == gate.state, 'Durable ledger changed outside owner')
    entries = [x for x in gate.state['reservations'] if x['attempt_id'] == slot['slot_id']]
    r.require(len(entries) == 1, 'One reservation for this exact slot required')
    entry = entries[0]
    r.require(entry['status'] == 'COMPLETED' and 'dispatch_started_at_epoch' in entry and
              entry['task_id'] == slot['stage_id'], 'Uncompleted reservation cannot become acceptance')
    request = r.read(folder / 'request.json')
    response = r.read(folder / 'response.json')
    saved_response = gate.directory / ('response-%03d.json' % entry['sequence'])
    r.require(entry['prompt'] == request and r.read(saved_response) == response,
              'Request/response does not belong to this reservation')
    r.check_response(response, set())
    return dict(schema='repodisco-growth-current-request-provenance-v1', execution_run_id=run_id,
                runtime_sha256=runtime_sha, slot_id=slot['slot_id'], lineage_id=slot['lineage_id'],
                stage_id=slot['stage_id'], reservation_sequence=entry['sequence'],
                request_sha256=r.sha((folder / 'request.json').read_bytes()),
                response_sha256=r.sha((folder / 'response.json').read_bytes()),
                ledger_response_sha256=r.sha(saved_response.read_bytes()), provider_request_id=response['request_id'],
                reservation_sha256=r.sha(r.canonical(entry)), guard_sha256=r.sha((folder / 'guard.json').read_bytes()),
                source_manifest_sha256=r.sha((folder / 'source-manifest.json').read_bytes()),
                candidate_revision_sha256=api.b.digest_map(api.b.source_hashes(sources)))


@dataclass
class Parent:
    slot: dict
    folder: Path
    binding: object
    provenance: dict
    head: dict


def persist_native(folder, result, api):
    for name, raw in result.artifacts.items():
        api.b.path_name(name)
        r.require(name not in ('accepted.json', 'native-units.json'), 'Verifier cannot issue acceptance')
        write_bytes(folder / 'evidence' / name, raw)
    write_bytes(folder / 'evidence/native-units.json', api.b.canonical(result.extraction))
    durable_json(folder / 'native-binding.json', asdict(result.binding))


def load_evidence(parent, api):
    metadata = {name: r.pinned_path(parent.folder / 'evidence', name).read_bytes()
                for name, _ in parent.binding.native.artifact_sha256}
    return {**metadata, **{name: (parent.folder / 'evidence' / name).read_bytes()
                          for name in ('accepted.json', 'native-units.json')}}


def accepted_parent(slot, parent, gate, original, api, repo, run_id, runtime_sha, heads, synthetic):
    r.require(parent.slot['slot_id'] == slot['parent_slot'] and parent.slot['lineage_id'] == slot['lineage_id'],
              'Wrong current-run parent slot or lineage')
    sources = load_sources(parent.folder, original, api)
    response = r.read(parent.folder / 'response.json')
    body, envelope = parse_body(response, parent.slot['stage_id'], api)
    rebuilt, guard = api.b.reconstruct(parent.slot['stage_id'], body, original, chain_id=slot['lineage_id'])
    guard['envelope'] = envelope
    r.require(rebuilt == sources and r.read(parent.folder / 'guard.json') == guard,
              'Accepted source is not this saved response reconstructed under its guard')
    current = provenance(parent.folder, parent.slot, gate, sources, api, run_id, runtime_sha)
    r.require(current == parent.provenance and r.read(heads / (slot['lineage_id'] + '.json')) == parent.head,
              'Accepted parent request provenance or promoted head changed')
    evidence = load_evidence(parent, api)
    receipt = api.b.read_json(evidence['accepted.json'])
    r.require(receipt.get('host_request_provenance') == current and
              r.read(parent.folder / 'native-binding.json') == json.loads(r.encode(asdict(parent.binding.native))),
              'Receipt/native run is not bound to this completed model request')
    api.validate_accepted_parent(slot['stage_id'], slot['lineage_id'], sources, parent.binding, evidence,
                                 allow_synthetic=synthetic, repo=repo)
    return sources, evidence


def issue_parent(folder, slot, sources, result, request_provenance, api, heads, synthetic):
    native = result.binding
    extraction_raw = api.b.canonical(result.extraction)
    receipt = dict(schema='repodisco-growth-host-accepted-stage-one-v3', status='accepted', stage=1,
                   project=slot['project'], chain_id=slot['lineage_id'], run_id=native.run_id,
                   origin=native.origin, source_revision_sha256=native.source_revision_sha256,
                   source_sha256=api.b.source_hashes(sources), policy_sha256=api.b.policy_digest(),
                   native_binding_sha256=api.b.sha(api.b.canonical(asdict(native))),
                   native_extraction_sha256=api.b.sha(extraction_raw),
                   qualification_gate_sha256=api.b.sha(result.artifacts['qualification-gate.json']),
                   host_scope_sha256=result.extraction['host_scope_sha256'],
                   host_request_provenance=request_provenance, synthetic_offline_fixture=synthetic)
    raw = api.b.canonical(receipt)
    write_bytes(folder / 'evidence/accepted.json', raw)
    binding = api.AcceptedParentBinding(native, slot['lineage_id'], api.b.sha(raw), api.b.sha(extraction_raw))
    durable_json(folder / 'accepted-parent-binding.json', asdict(binding))
    head = dict(status='accepted', stage=1, slot_id=slot['slot_id'], lineage_id=slot['lineage_id'],
                source_revision_sha256=native.source_revision_sha256,
                receipt_sha256=binding.receipt_sha256, synthetic=synthetic)
    return Parent(slot, folder, binding, request_provenance, head)


def _execute(repo, out, transport, verifier, deadline, package, *, validate, clock=time.time,
             synthetic=False, audit_native=None, run_id=None, authority=None, execution_claim=None, environment=None):
    """Shared deterministic state machine. Only the CLI below selects live dependencies."""
    repo, out = Path(repo).resolve(), Path(out)
    renderer, api = r.load_context(repo)
    r.require(getattr(verifier, 'synthetic', None) is synthetic, 'Verifier origin mismatch')
    if audit_native is None:
        from native_host import audit_result
        audit_native = audit_result
    run_id = run_id or ('synthetic-' if synthetic else 'growth-') + uuid.uuid4().hex
    r.require(bool(api.b.IDENTITY.fullmatch(run_id)), 'Invalid run identity')
    r.require(synthetic or isinstance(authority, bytes) and isinstance(execution_claim, bytes),
              'Live authorization and exclusive execution claim required')
    out.mkdir(parents=True, exist_ok=False)
    heads = out / 'accepted-heads'
    heads.mkdir()
    durable_json(out / 'run.json', dict(schema='repodisco-sequential-growth-run-v1', run_id=run_id,
                 synthetic=synthetic, model_calls_authorized=0 if synthetic else r.LIMIT,
                 package=package, deadline=deadline, no_resume=True, started_at_epoch=clock(),
                 authorization_sha256=None if authority is None else r.sha(authority),
                 execution_claim_sha256=None if execution_claim is None else r.sha(execution_claim)))
    if authority is not None:
        write_bytes(out / 'authorization.json', authority)
    if execution_claim is not None:
        write_bytes(out / 'execution.claim.json', execution_claim)
    durable_json(out / 'environment.json', environment or dict(synthetic_offline_fixture=True))
    durable_json(out / 'archive-exclusions.json', dict(
        excluded_generated_cargo_targets=[f'slot-{n:02d}/native/fresh-target' for n in range(1, r.LIMIT + 1)],
        raw_native_outputs_and_sources_excluded=False))
    gate = RequestGate(out / 'requests', r.LIMIT, deadline, transport, clock=clock)
    parents, originals, rows, ids = {}, {}, [], set()
    fatal, verifier_attempts, invocation_counts = None, 0, []
    try:
        for slot in package['order']:
            validate()
            r.require(clock() < deadline, 'Run deadline reached')
            folder = out / slot['slot_id']
            folder.mkdir()
            durable_json(folder / 'slot.json', slot)
            row = dict(**slot, synthetic=synthetic)
            if slot['stage'] == 2 and slot['lineage_id'] not in parents:
                row.update(outcome='BLOCKED_PARENT', provider_request_made=False)
                rows.append(row)
                durable_json(folder / 'result.json', row)
                durable_json(out / 'results.json', rows)
                continue
            original = originals.setdefault(slot['project'], original_sources(repo, slot['project'], api))
            kwargs = dict(chain_id=slot['lineage_id'])
            if slot['stage'] == 1:
                source_parent = original
                rendered = renderer.render_stage1(slot['slot_id'])
                frozen = repo / r.PILOT / 'frozen-001/stage1' / (slot['slot_id'] + '.payload.json')
                r.require(renderer.encode(rendered['payload']) == frozen.read_bytes(), 'First-stage prompt drift')
            else:
                parent = parents[slot['lineage_id']]
                source_parent, evidence = accepted_parent(slot, parent, gate, original, api, repo,
                                                          run_id, package['runtime_sha256'], heads, synthetic)
                kwargs.update(parent_binding=parent.binding, parent_artifacts=evidence, allow_synthetic=synthetic)
                rendered = (renderer.render_synthetic_stage2_for_tests(slot['slot_id'], source_parent,
                            parent.binding, evidence, acknowledge_synthetic=True) if synthetic else
                            renderer.render_stage2(slot['slot_id'], source_parent, parent.binding, evidence))
            write_bytes(folder / 'request.json', renderer.encode(rendered['payload']))
            durable_json(folder / 'rendering.json', rendered['rendering'])
            response = gate.invoke(rendered['payload'], task_id=slot['stage_id'], attempt_id=slot['slot_id'])
            durable_json(folder / 'response.json', response)
            r.check_response(response, ids)
            validate()
            api.b.load_assets()
            row.update(request_id=response['request_id'], usage=response['usage'],
                       retry_attempts=response['retry_attempts'], provider_request_made=not synthetic)
            if response['stop_reason'] == 'max_tokens':
                row['outcome'] = 'OUTPUT_TRUNCATED'
            else:
                try:
                    body, envelope = parse_body(response, slot['stage_id'], api)
                except (ValueError, TypeError, KeyError, RecursionError) as error:
                    # A policy/input failure is not a bad model answer.
                    validate()
                    api.b.load_assets()
                    row.update(outcome='GUARD_REJECTED', rejection_type=type(error).__name__,
                               rejection_message=str(error)[:512])
                else:
                    # Parent, integrity and native exceptions are terminal, never ordinary guard rejections.
                    sources, guard = api.b.reconstruct(slot['stage_id'], body, source_parent, **kwargs)
                    guard['envelope'] = envelope
                    durable_json(folder / 'guard.json', guard)
                    save_sources(folder, sources, original, api)
                    request_origin = provenance(folder, slot, gate, sources, api, run_id, package['runtime_sha256'])
                    durable_json(folder / 'request-provenance.json', request_origin)
                    native_id = run_id + ':' + slot['slot_id']
                    verifier_attempts += 1
                    result = verifier.verify(slot, dict(sources), folder / 'native', native_id)
                    invocation_counts.append(result.native_invocations)
                    r.require(result.native_invocations in (0, 1, None), 'Invalid native invocation accounting')
                    row['native_invocations'] = result.native_invocations
                    if result.binding is None or result.extraction is None:
                        r.require(result.terminal is True, 'Missing native evidence cannot continue')
                        row.update(outcome=result.classification, native_terminal=True, native_run_id=native_id,
                                   qualified_pass=False, native_evidence_incomplete=True)
                        rows.append(row)
                        durable_json(folder / 'result.json', row)
                        raise RuntimeError('Native execution or evidence incomplete')
                    r.require(result.binding.run_id == native_id and result.binding.project == slot['project'] and
                              result.binding.stage == slot['stage'] and result.synthetic is synthetic and
                              result.binding.origin == ('synthetic-offline' if synthetic else 'model-candidate'),
                              'Native result belongs to a different invocation')
                    audit = audit_native(slot, sources, result, repo, allow_synthetic=synthetic)
                    extraction = result.extraction
                    r.require(audit['extraction_sha256'] == r.sha(api.b.canonical(extraction)) and
                              audit['qualified_pass'] == extraction['qualified_pass'] and
                              audit['classification'] == result.classification and audit['terminal'] == result.terminal,
                              'Native extraction or classification differs from replay')
                    durable_json(folder / 'native-audit.json', audit)
                    r.require(load_sources(folder, original, api) == sources, 'Candidate changed during verification')
                    persist_native(folder, result, api)
                    row.update(outcome=result.classification, native_terminal=result.terminal,
                               native_run_id=native_id, source_revision_sha256=result.binding.source_revision_sha256,
                               parent_api_calls=guard['body']['parent_api_calls'], qualified_pass=extraction['qualified_pass'])
                    if result.terminal:
                        rows.append(row)
                        durable_json(folder / 'result.json', row)
                        raise RuntimeError('Native execution/integrity stop')
                    if extraction['qualified_pass']:
                        # Rebind to the exact persisted request immediately before publishing acceptance.
                        r.require(request_origin == provenance(folder, slot, gate, sources, api, run_id,
                                                               package['runtime_sha256']), 'Request provenance changed')
                        row['outcome'] = 'ACCEPTED'
                        if slot['stage'] == 1:
                            parent = issue_parent(folder, slot, sources, result, request_origin, api, heads, synthetic)
                            evidence = load_evidence(parent, api)
                            child_id = api.STAGES[slot['project']][1]
                            api.validate_accepted_parent(child_id, slot['lineage_id'], sources, parent.binding,
                                                         evidence, allow_synthetic=synthetic, repo=repo)
                            durable_json(heads / (slot['lineage_id'] + '.json'), parent.head)
                            parents[slot['lineage_id']] = parent
                        else:
                            receipt = dict(schema='repodisco-growth-stage-two-acceptance-v1', status='accepted',
                                synthetic=synthetic, lineage_id=slot['lineage_id'], slot_id=slot['slot_id'],
                                native_binding_sha256=r.sha(r.canonical(asdict(result.binding))),
                                native_extraction_sha256=r.sha(api.b.canonical(extraction)),
                                host_request_provenance=request_origin,
                                accepted_parent_binding_sha256=r.sha(r.canonical(asdict(parents[slot['lineage_id']].binding))),
                                source_revision_sha256=result.binding.source_revision_sha256)
                            durable_json(folder / 'accepted-stage-two.json', receipt)
                            durable_json(heads / (slot['lineage_id'] + '.json'), dict(status='accepted', stage=2,
                                slot_id=slot['slot_id'], lineage_id=slot['lineage_id'], synthetic=synthetic,
                                source_revision_sha256=result.binding.source_revision_sha256,
                                receipt_sha256=r.sha((folder / 'accepted-stage-two.json').read_bytes())))
            rows.append(row)
            durable_json(folder / 'result.json', row)
            durable_json(out / 'results.json', rows)
            print(slot['slot_id'], row['outcome'], flush=True)
    except BaseException as error:
        fatal = dict(error_type=type(error).__name__, after_completed_rows=len(rows),
                     no_retry=True, no_resume=True)
        durable_json(out / 'stop.json', fatal)
    finally:
        complete = fatal is None and len(rows) == r.LIMIT
        if not gate.closed:
            gate.close('completed' if complete else 'terminal_stop')
        durable_json(out / 'results.json', rows)
        reservations = gate.state['reservations']
        summary = dict(status='SYNTHETIC_COMPLETE' if synthetic and complete else
                       'COMPLETE' if complete else 'SYNTHETIC_STOPPED' if synthetic else 'STOPPED',
            synthetic=synthetic, proposed_max_calls=r.LIMIT,
            model_requests_reserved=0 if synthetic else len(reservations),
            transport_reservations=len(reservations),
            completed_responses=sum(x['status'] == 'COMPLETED' for x in reservations),
            ambiguous_or_unsaved=sum(x['status'] == 'AMBIGUOUS_OR_UNSAVED' for x in reservations),
            dispatched_slots=[x['attempt_id'] for x in reservations if 'dispatch_started_at_epoch' in x],
            blocked_children=[x['slot_id'] for x in rows if x['outcome'] == 'BLOCKED_PARENT'],
            unprocessed_slots=[x['slot_id'] for x in package['order'] if x['slot_id'] not in {z['slot_id'] for z in rows}],
            unused_capacity_never_reassigned=r.LIMIT-len(reservations),
            accepted_stages=sum(x['outcome'] == 'ACCEPTED' for x in rows),
            completed_lineages=sum(x['outcome'] == 'ACCEPTED' and x['stage'] == 2 for x in rows),
            verifier_adapter_calls=verifier_attempts,
            native_calls=0 if synthetic else sum(invocation_counts) if
                len(invocation_counts)==verifier_attempts and None not in invocation_counts else None,
            confirmed_native_invocations=0 if synthetic else sum(x for x in invocation_counts if x is not None),
            native_invocations_unknown=0 if synthetic else invocation_counts.count(None)+verifier_attempts-len(invocation_counts),
            native_call_accounting='Synthetic tests invoke no verifier; real counts follow explicit native adapter invocation records.',
            fatal=fatal, original_results_changed=False)
        durable_json(out / 'summary.json', summary)
        manifest = {p.relative_to(out).as_posix(): r.sha(p.read_bytes()) for p in r.archive_files(out)}
        durable_json(out / 'archive-manifest.json', manifest)
    return summary


def simulate(repo, out, transport, verifier, *, deadline, acknowledge_synthetic=False,
             clock=time.time, package=None, validate=None, audit_native=None, run_id=None):
    r.require(acknowledge_synthetic is True, 'Explicit synthetic test opt-in required')
    package = package or r.validate_package(repo)
    return _execute(repo, out, transport, verifier, deadline, package, synthetic=True, clock=clock,
                    validate=validate or (lambda: r.validate_package(repo)), audit_native=audit_native, run_id=run_id)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--authorization', type=Path, required=True)
    parser.add_argument('--handoff', type=Path, default=Path.home()/'.repodisco-bedrock-handoff')
    args = parser.parse_args(argv)
    auth = r.validate_authorization(args.authorization, args.repo)
    package = r.validate_package(args.repo)
    auth_raw = args.authorization.read_bytes()
    r.require(os.environ.get('SLURM_JOB_ID', '').isdigit() and os.environ.get('SLURM_CPUS_PER_TASK') == '1' and
              'login' not in socket.gethostname().lower(), 'One-CPU compute allocation required')
    r.require(not args.output.exists() and not args.output.is_symlink(), 'Output exists; no restart')
    actual_root = args.repo.resolve().parent
    r.require(str(actual_root) == auth['authorized_runtime_root'] and
              args.output.absolute() == actual_root / 'model-001' and
              args.repo.resolve() == actual_root / 'repo', 'Authorization is bound to another execution directory')
    # This fixed scope-wide claim survives even an empty/missing output directory.
    # Changing --output or copying this runtime cannot reuse the authorization.
    write_bytes(actual_root / 'execution.claim.json', r.encode(dict(execution_id=r.EXECUTION_ID,
                 authorization_sha256=r.sha(auth_raw), runtime_sha256=package['runtime_sha256'],
                 job_id=os.environ['SLURM_JOB_ID'], output=str(args.output), no_resume=True)))
    fd = os.open(actual_root, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    from native_host import NativeVerifier
    backend = None
    packages = {}
    for name in ('boto3', 'botocore'):
        try:
            packages[name] = version(name)
        except PackageNotFoundError:
            packages[name] = None
    environment = dict(python=sys.version, packages=packages, hostname=socket.gethostname(),
                       job_id=os.environ['SLURM_JOB_ID'], cpus_per_task=1,
                       partition=os.environ.get('SLURM_JOB_PARTITION'), credentials_recorded=False)

    def validate():
        r.require(args.authorization.read_bytes() == auth_raw, 'Authorization changed during run')
        r.require(r.validate_package(args.repo) == package, 'Runtime inputs changed')
        r.validate_authorization(args.authorization, args.repo)

    def transport(payload):
        nonlocal backend
        validate()
        if backend is None:
            r.require(all(packages.values()), 'SDK packages missing; credential handoff not consumed')
            try:
                consume_key(args.handoff)
                backend = bedrock_transport(package['settings'])
            finally:
                # Keep credentials out of native verifier subprocess environments.
                os.environ.pop('AWS_BEARER_TOKEN_BEDROCK', None)
        return backend(payload)

    summary = _execute(args.repo, args.output, transport, NativeVerifier(args.repo),
                       auth['expires_at_epoch'], package, validate=validate, authority=auth_raw,
                       execution_claim=(actual_root/'execution.claim.json').read_bytes(), environment=environment)
    r.require(summary['status'] == 'COMPLETE', 'Run stopped; inspect preserved evidence, never restart')


if __name__ == '__main__':
    main()
