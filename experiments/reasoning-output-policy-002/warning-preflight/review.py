"""Review one analyst-authored warning-alias check; never rescore original output."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))
from evidence_audit import archive_check, classify_existing_evidence, exact_hashes, PILOT


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def load(path): return json.loads(path.read_text())
def require(condition, message):
    if not condition: raise ValueError(message)


def review():
    output = ROOT / 'verification-001'
    manifest = ROOT / 'manifest.json'
    require(sha(manifest) == '995fc777bf4e603cc34a4390fcf0a6df0d527b5d2a9789b95c386d8a930cf07e', 'Manifest drift')
    require(sha(output / 'snapshot/manifest.json') == sha(manifest), 'Snapshot manifest drift')
    for name, expected in load(manifest).items():
        require(sha(ROOT / name) == sha(output / 'snapshot' / name) == expected, 'Input drift: ' + name)
    from verify import guarded_sources
    sources = guarded_sources()
    record = load(output / 'alias-case.json')
    evidence = record['evidence']
    exact_hashes({name: data.decode() for name, data in sources.items()}, evidence)
    require(record['mutation'] == load(ROOT / 'mutation.json') and record['model_calls'] == 0, 'Mutation drift')
    require(evidence['attempts'] == 1 and evidence['model_calls'] == 0, 'Invocation count drift')
    require(evidence['command'] == ['timeout','-k','5s','60s','dafny','verify','--verify-included-files','All.dfy'], 'Verifier flags changed')
    env = load(output / 'environment.json')
    require(env['job_id'] == '57178004' and env['partition'] == 'test' and 'login' not in env['host'], 'Compute identity mismatch')
    require(env['dafny'] == '4.11.0+fcb2042d6d043a2634f0854338c08feeaaaf4ae2' and
            env['z3'] == 'Z3 version 4.12.1 - 64 bit', 'Verifier version drift')
    summary = load(output / 'summary.json')
    require(summary['completed_cases'] == 1 and summary['exit_code'] == evidence['exit_code'], 'Summary mismatch')
    classification = classify_existing_evidence(evidence)
    require(classification == dict(category='strict_success', exit_code=0, verified_obligations=16,
                                   verification_errors=0, diagnostic_warnings=0), 'Unexpected diagnostic result')
    original_archive = archive_check(PILOT / 'model-001', PILOT / 'model-001-sha256.json')
    require(load(PILOT / 'results-review.json')['verified'] == 18, 'Original score changed')
    result = dict(status='strict_success', job_id='57178004', new_model_calls=0,
                  new_verifier_invocations=1, analyst_authored=True, original_pilot_score='18/24 unchanged',
                  original_trial24='OUTPUT_REJECTED; separate unaltered-body diagnostic remains warning-only exit 2',
                  mutation='15 concrete-map expressions replaced by existing lhs/rhs aliases from first forall onward',
                  new_lemma_calls=0, contracts_and_other_eight_files_unchanged=True,
                  policy_sha256=sha(ROOT / 'code/body_guard.py'), source_sha256=evidence['source_sha256'],
                  manifest_sha256=sha(manifest), record_sha256=sha(output / 'alias-case.json'),
                  review_script_sha256=sha(ROOT / 'review.py'), result=classification,
                  original_archive_check=original_archive,
                  interpretation='One observed warning can be removed with admitted ordinary syntax under unchanged strict flags; not a general trigger guarantee or new model success.')
    (ROOT / 'review.json').write_text(json.dumps(result, indent=2) + '\n')
    (ROOT / 'verification-001-sha256.json').write_text(json.dumps(
        {str(p.relative_to(output)): sha(p) for p in sorted(output.rglob('*')) if p.is_file()}, indent=2) + '\n')
    print(json.dumps({key:value for key,value in result.items() if key not in ('source_sha256','original_archive_check')},indent=2))


if __name__ == '__main__': review()
