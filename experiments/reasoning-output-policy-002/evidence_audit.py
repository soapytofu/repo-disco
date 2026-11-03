"""Reconstruct saved inputs offline and link byte-identical verifier evidence.

This script performs no verification, model requests, acceptance, or rescoring.
It writes only its own audit report. Existing evidence archives are read-only.
"""
import collections
import hashlib
import json
from pathlib import Path
import re

from body_guard import VERSION, digest, parse_response, split_seed

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
EXPANSION = ROOT.parent / 'monorepo-reasoning-expansion-001'
REVISION = EXPANSION / 'revision-003'
PILOT = ROOT.parent / 'monorepo-reasoning-calibration-pilot-001'
DIAGNOSTIC = ROOT.parent / 'reasoning-response-diagnostic-001'
OLD_GUARD = '5cb8995fe7108538e9d7debb561dc75c38c895d5dd739a7bcf4673aaeeec1102'
COMPLETION_REVIEW = '888ac0a847614097a1db62f854fbbe07d497490f51c00ee28d2506e00101fdf0'
ORIGINAL_ARCHIVE = 'a113a4b16bb4bf30c49eaf5a059c77b475351ea015c4622aca211bb66fdfa766'
DIAGNOSTIC_ARCHIVE = '007cdd0850cefa09759c6908db7a1fb7e37104cfa3abeae84b3ffdec8690c8c8'
FROZEN_PROPOSAL = '56dc93326ba4ebaa7ba6d5787207665c3ed89f81cf2f5703362b2815640d0afc'
SUMMARY = re.compile(r'^Dafny program verifier finished with (\d+) verified, (\d+) errors?\s*$', re.MULTILINE)


def load(path): return json.loads(path.read_text())
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def files(path): return {p.name: p.read_text() for p in path.glob('*.dfy')}
def relative(path): return str(path.relative_to(REPO))
def require(condition, message):
    if not condition: raise ValueError(message)


def exact_hashes(sources, evidence):
    actual = {name: digest(source) for name, source in sources.items()}
    require(actual == evidence['source_sha256'], 'Candidate/evidence source bytes differ')
    return actual


def classify_existing_evidence(evidence):
    """Classify only the three observed saved-response outcomes, fail on others.

    No return value is an acceptance decision. In particular a warning-only
    nonzero exit remains non-success under the original strict policy.
    """
    text = evidence['stdout'] + '\n' + evidence['stderr']
    summaries = SUMMARY.findall(text)
    require(len(summaries) == 1, 'Missing or ambiguous verifier summary')
    verified, errors = map(int, summaries[0])
    code = evidence['exit_code']
    warning_count = len(re.findall(r'^.*?: Warning:', text, re.MULTILINE))
    error_diagnostic = bool(re.search(r'^.*?: Error:', text, re.MULTILINE))
    if code == 0 and errors == 0 and not error_diagnostic and warning_count == 0:
        category = 'strict_success'
    elif code == 4 and errors > 0 and error_diagnostic and 'assertion might not hold' in text:
        require('parse error' not in text.lower(), 'Parse errors are not assertion failures')
        category = 'assertion_failure'
    elif (code == 2 and errors == 0 and not error_diagnostic and warning_count > 0 and
          'Compilation failed because warnings were found and --allow-warnings is false' in text):
        category = 'warning_only_nonzero_exit'
    else:
        raise ValueError('Unexpected or inconsistent saved-response diagnostic')
    return dict(category=category, exit_code=code, verified_obligations=verified,
                verification_errors=errors, diagnostic_warnings=warning_count)


def archive_check(root, manifest):
    expected = load(manifest)
    actual = {str(p.relative_to(root)): sha(p) for p in root.rglob('*') if p.is_file()}
    require(actual == expected, 'Previously published archive drift: ' + relative(root))
    return dict(path=relative(manifest), sha256=sha(manifest), files=len(actual))


def audit():
    require(sha(PILOT / 'model-001-sha256.json') == ORIGINAL_ARCHIVE, 'Original archive manifest changed')
    require(sha(DIAGNOSTIC / 'verification-001-sha256.json') == DIAGNOSTIC_ARCHIVE, 'Diagnostic manifest changed')
    require(sha(PILOT / 'frozen-001/freeze.json') == FROZEN_PROPOSAL, 'Frozen proposal changed')
    for name, expected in load(PILOT / 'frozen-001/freeze.json')['files'].items():
        require(sha(PILOT / 'frozen-001' / name) == expected, 'Frozen input changed: ' + name)
    archives = [archive_check(PILOT / 'model-001', PILOT / 'model-001-sha256.json'),
                archive_check(DIAGNOSTIC / 'verification-001', DIAGNOSTIC / 'verification-001-sha256.json')]
    for old in [EXPANSION / 'protocol/body_guard.py', PILOT / 'frozen-001/guard/body_guard.py']:
        require(sha(old) == OLD_GUARD, 'Old guard changed')
    require(sha(REVISION / 'completion-review.json') == COMPLETION_REVIEW, 'Fixture evidence review drift')
    fixture_review = load(REVISION / 'completion-review.json')
    reviewed = {(row['task_id'], row['variant']): row for row in fixture_review['rows']}
    tasks = {t['task_id']: t for t in load(REVISION / 'tasks.json')}
    controls = []
    for check in load(REVISION / 'checks.json'):
        if check['variant'] in ('hidden_shortcut', 'weaken_contract'):
            continue  # Intentionally forbidden edits are tested as rejections.
        task = tasks[check['task_id']]
        seed = files(REVISION / 'fixtures' / task['task_id'] / 'empty')
        target = files(REVISION / check['path'])
        bodies = {}
        for name in task['editable_files']:
            prefix, suffix = split_seed(seed[name])
            require(target[name].startswith(prefix) and target[name].endswith(suffix), 'Fixture protected-byte drift')
            bodies[name] = target[name][len(prefix):-len(suffix)]
        candidate, decision = parse_response(json.dumps(bodies), seed, task)
        require(candidate == target, 'Fixture reconstruction differs')
        row = reviewed[(task['task_id'], check['variant'])]
        record = EXPANSION / row['evidence']
        require(sha(record) == row['evidence_sha256'], 'Fixture raw evidence drift')
        hashes = exact_hashes(candidate, row)
        raw_record = load(record)
        raw_evidence = raw_record.get('evidence', raw_record)
        exact_hashes(candidate, raw_evidence)
        controls.append(dict(task_id=task['task_id'], variant=check['variant'],
                             previously_observed_category=row['diagnostic'],
                             evidence_path=relative(record), evidence_sha256=sha(record),
                             candidate_sha256=hashes, admission=True))

    frozen_tasks = {t['task_id']: t for t in load(PILOT / 'frozen-001/tasks.json')}
    diagnostic_rows = {r['original_trial']: r for r in load(DIAGNOSTIC / 'diagnostic-review.json')['rows']
                       if r['unchanged_body_strings']}
    responses = []
    for trial in load(PILOT / 'frozen-001/trials.json'):
        task = frozen_tasks[trial['task_id']]
        original = PILOT / 'model-001' / trial['trial_id']
        response_path = original / 'response.json'
        raw = load(response_path)['text']
        seed = files(PILOT / 'frozen-001/tasks' / trial['task_id'])
        candidate, decision = parse_response(raw, seed, task)
        result = load(original / 'result.json')
        if result['outcome'] == 'OUTPUT_REJECTED':
            case = diagnostic_rows[trial['trial_id']]
            record = DIAGNOSTIC / 'verification-001' / (case['case_id'] + '.json')
            require(sha(record) == case['record_sha256'], 'Diagnostic raw evidence drift')
            saved = load(record)
            require(saved['case']['unchanged_body_strings'] and saved['case']['mutation'] is None,
                    'Only unaltered-body evidence may be reused')
            require(saved['case']['original_response_sha256'] == sha(response_path), 'Original response differs')
            target = files(DIAGNOSTIC / 'fixtures' / case['case_id'])
            evidence = saved['evidence']
            evidence_origin = 'separate_unaltered_body_diagnostic'
        else:
            record = original / 'verification.json'
            evidence = load(record)
            target = files(original / 'candidate')
            evidence_origin = 'original_pilot'
        require(candidate == target, 'Saved response bytes were changed')
        hashes = exact_hashes(candidate, evidence)
        for name in set(seed) - set(task['editable_files']):
            require(candidate[name] == seed[name], 'Protected source changed')
        semantic = classify_existing_evidence(evidence)
        require(decision['semantic_verification_performed'] is False, 'Parser must not claim verification')
        responses.append(dict(trial_id=trial['trial_id'], task_id=trial['task_id'],
                              original_outcome=result['outcome'], admission=True,
                              response_path=relative(response_path), response_sha256=sha(response_path),
                              body_strings_preserved=True, protected_source_preserved=True,
                              candidate_sha256=hashes, parser_decision=decision,
                              evidence_origin=evidence_origin, evidence_path=relative(record),
                              evidence_sha256=sha(record), prior_semantic_evidence=semantic))

    original_review = load(PILOT / 'results-review.json')
    require(original_review['verified'] == 18 and original_review['returned'] == 24, 'Original score changed')
    counts = collections.Counter(row['variant'] == 'reference' for row in controls)
    require(counts == {True: 24, False: 104} and len(responses) == 24, 'Incomplete compatibility coverage')
    require(collections.Counter(row['evidence_origin'] for row in responses) ==
            {'original_pilot': 19, 'separate_unaltered_body_diagnostic': 5}, 'Unexpected evidence sources')
    report = dict(policy_version=VERSION, parser_sha256=sha(ROOT / 'body_guard.py'),
                  audit_script_sha256=sha(ROOT / 'evidence_audit.py'), new_model_calls=0,
                  new_verifier_invocations=0, original_pilot_score='18/24 unchanged',
                  interpretation='Post-hoc syntax compatibility and byte-identical evidence reuse; not a new prospective score.',
                  unchanged_archives=archives, unchanged_old_guard_sha256=OLD_GUARD,
                  fixture_completion_review_sha256=COMPLETION_REVIEW,
                  offline_reference_reconstructions=24, offline_negative_reconstructions=104,
                  saved_response_admissions=24, fixture_controls=controls, saved_responses=responses)
    return report


if __name__ == '__main__':
    report = audit()
    (ROOT / 'compatibility-audit.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({key: value for key, value in report.items()
                      if key not in ('fixture_controls', 'saved_responses')}, indent=2))
