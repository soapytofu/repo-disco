"""Replay persisted proof edits and audit all request evidence without dispatching."""
from collections import Counter
import json
from pathlib import Path
import run_pilot as r


def review(root=r.ROOT):
    out = root / 'model-001'
    plan, tasks, trials = r.validate_bundle(root)
    pins = r.validate_runtime(root)
    r.require(r.inventory(out / 'frozen-001') == r.inventory(root / 'frozen-001'), 'Archived proposal mismatch')
    r.require(r.inventory(out / 'inputs') == r.inventory(root / 'inputs'), 'Archived dependencies mismatch')
    r.require(r.sha(out / 'runtime-freeze.json') == r.sha(root / 'runtime-freeze.json'), 'Runtime freeze mismatch')
    r.require(r.inventory(out / 'runtime') == pins['runtime_sha256'], 'Archived runtime mismatch')
    auth = r.load(out / 'authorization.json')
    r.require(auth['authorized'] and auth['max_calls'] == 8 and not auth['automatic_retries']
              and not auth['reassign_unused'] and auth['proposal_freeze_sha256'] == r.PROPOSAL_SHA
              and auth['runtime_freeze_sha256'] == r.sha(root / 'runtime-freeze.json'), 'Authorization mismatch')
    env = r.load(out / 'environment.json')
    r.require(env['dafny'] == plan['verifier']['toolchain'] and env['z3'] == plan['verifier']['z3']
              and env['job_id'] and 'login' not in env['host'], 'Compute toolchain/provenance mismatch')
    guard = r.guard_module(root)
    ledger = r.load(out / 'requests/ledger.json')
    reservations = ledger['reservations']
    r.require(ledger['limit'] == 8 and len(reservations) <= 8 and
              ledger['deadline'] == auth['expires_at_epoch'], 'Ledger budget/deadline mismatch')
    rows, ids, tokens = [], set(), Counter()
    for index, reservation in enumerate(reservations):
        trial = trials[index]
        task = next(t for t in tasks if t['task_id'] == trial['task_id'])
        folder = out / trial['trial_id']
        r.require(reservation['sequence'] == index+1 and reservation['attempt_id'] == trial['trial_id']
                  and reservation['task_id'] == trial['task_id'], 'Dispatch order mismatch')
        r.require(reservation['prompt'] == r.load(root / 'frozen-001' / trial['request_path'])
                  and r.sha(folder / 'request.json') == trial['request_sha256'], 'Request bytes changed')
        r.require(r.load(folder / 'trial.json') == trial and r.load(folder / 'task.json') == task, 'Trial metadata')
        if 'dispatch_started_at_epoch' in reservation:
            r.require(reservation['dispatch_started_at_epoch'] < auth['expires_at_epoch'], 'Dispatch after deadline')
        result_path = folder / 'result.json'
        result = r.load(result_path) if result_path.exists() else {'outcome': 'INCOMPLETE_RECORD'}
        row = dict(**trial, outcome=result['outcome'], depth=task['depth'], sharing=task['sharing'],
                   reserved=True, dispatched='dispatch_started_at_epoch' in reservation,
                   returned=False, admitted=False, verified=False, diagnostic_labels=[])
        if reservation['status'] != 'COMPLETED':
            rows.append(row)
            continue
        response = r.load(out / 'requests' / f'response-{index+1:03d}.json')
        r.require(response == r.load(folder / 'response.json'), 'Persisted responses differ')
        raw = response['raw_response']
        rid = response['request_id']
        r.require(isinstance(rid, str) and rid and rid not in ids, 'Duplicate/missing request ID')
        r.require(response['retry_attempts'] == raw['ResponseMetadata']['RetryAttempts'] == 0, 'SDK retry')
        r.require(raw['ResponseMetadata']['RequestId'] == rid == result['request_id'], 'Request ID mismatch')
        r.require(raw['output']['message']['content'] == response['content']
                  and ''.join(b['text'] for b in response['content'] if 'text' in b) == response['text'],
                  'Provider content mismatch')
        r.require(raw.get('usage') == response.get('usage') and raw.get('stopReason') == response['stop_reason'],
                  'Usage/stop metadata mismatch')
        ids.add(rid)
        row.update(returned=True, request_id=rid, usage=response.get('usage'),
                   elapsed_seconds=result['elapsed_seconds'])
        for key, value in (response.get('usage') or {}).items():
            if isinstance(value, (int, float)):
                tokens[key] += value
        extraction = r.load(folder / 'extraction.json')
        if response['stop_reason'] == 'max_tokens':
            r.require(result['outcome'] == 'OUTPUT_TRUNCATED' and
                      extraction == dict(accepted=False, stage='truncation'), 'Truncation mismatch')
        else:
            seed = r.sources(root, task)
            try:
                candidate_text, decision = guard.parse_response(response['text'],
                                                                {n: b.decode() for n, b in seed.items()}, task)
            except (ValueError, TypeError, UnicodeError, RecursionError) as error:
                r.require(result['outcome'] == 'OUTPUT_REJECTED' and extraction ==
                          dict(accepted=False, error_type=type(error).__name__, reason=str(error)),
                          'Guard rejection mismatch')
                row['rejection_reason'] = str(error)
            else:
                r.require(extraction == dict(accepted=True, **decision), 'Guard decision mismatch')
                candidate = {n: s.encode() for n, s in candidate_text.items()}
                r.require(candidate == {p.name: p.read_bytes() for p in (folder / 'candidate').glob('*.dfy')},
                          'Candidate differs from exact response')
                r.require(r.load(folder / 'candidate-hashes.json') ==
                          dict(parent_sha256=r.hashes(seed), candidate_sha256=r.hashes(candidate)), 'Source hashes')
                row['admitted'] = True
                row['separate_bodies_identical'] = (
                    len({b['body_sha256'] for b in decision['bodies'].values()}) == 1
                    if task['sharing'] == 'separate' else None)
                verification_path = folder / 'verification.json'
                if not verification_path.exists():
                    r.require(result['outcome'] in ('VERIFIER_ERROR', 'INCOMPLETE_RECORD'), 'Missing verification')
                else:
                    verification = r.load(verification_path)
                    r.require(verification['source_sha256'] == r.hashes(candidate)
                              and verification['attempts'] == 1 and verification['model_calls'] == 0, 'Verifier provenance')
                    r.require(verification['command'] ==
                              ['timeout', '-k', '5s', '60s', 'dafny', 'verify', '--verify-included-files', 'All.dfy'],
                              'Verifier command mismatch')
                    r.require(result['outcome'] == r.outcome_for_evidence(verification), 'Outcome mismatch')
                    row['verified'] = result['outcome'] == 'VERIFIED'
                    text = (verification['stdout'] + '\n' + verification['stderr']).lower()
                    row['diagnostic_labels'] = [label for label, needle in
                        [('precondition', 'precondition'), ('postcondition', 'postcondition'),
                         ('assertion', 'assertion'), ('termination', 'decreases'),
                         ('parse', 'parse error'), ('resolution', 'unresolved'), ('warning', ': warning:')]
                        if needle in text]
                    row['verifier_exit_code'] = verification['exit_code']
                    if row['verified']:
                        r.require(r.load(folder / 'accepted.json') ==
                                  dict(parent_sha256=r.hashes(seed), candidate_sha256=r.hashes(candidate),
                                       editable_files=task['editable_files'],
                                       verification_sha256=r.sha(verification_path)), 'Accepted proof mismatch')
        if not row['admitted']:
            r.require(not (folder / 'candidate').exists() and not (folder / 'verification.json').exists(),
                      'Rejected output was verified')
        if not row['verified']:
            r.require(not (folder / 'accepted.json').exists(), 'Invalid accepted proof record')
        rows.append(row)

    completed = len(rows) == 8 and all(row['outcome'] in r.NORMAL_OUTCOMES and row['returned'] for row in rows)
    report = dict(planned=8, reserved=len(reservations), dispatched=sum(row['dispatched'] for row in rows),
                  returned=len(ids), unique_request_ids=len(ids), sdk_retries=0,
                  admitted=sum(row['admitted'] for row in rows), verified=sum(row['verified'] for row in rows),
                  all_completed=completed, outcomes=dict(Counter(row['outcome'] for row in rows)),
                  token_usage=dict(tokens), trials=rows)
    report['cells'] = [
        dict(depth=depth, sharing=sharing, planned=2, **{
            field: sum(row['depth'] == depth and row['sharing'] == sharing and row[field] for row in rows)
            for field in ('reserved', 'dispatched', 'returned', 'admitted', 'verified')})
        for depth in ('shallow', 'deep') for sharing in ('shared', 'separate')]
    summary = r.load(out / 'summary.json')
    r.require(summary['reserved_calls'] == report['reserved']
              and summary['completed_responses'] == report['returned']
              and summary['verified'] == report['verified']
              and summary['all_trials_processed'] == completed, 'Runtime summary mismatch')
    return report


if __name__ == '__main__':
    report = review()
    r.durable_json(r.ROOT / 'results-review.json', report)
    r.durable_json(r.ROOT / 'model-001-sha256.json', r.inventory(r.ROOT / 'model-001'))
    print(json.dumps({k: v for k, v in report.items() if k != 'trials'}, indent=2))
