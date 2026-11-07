"""Replay the extraction boundary and inspect compute evidence without new runs."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
PILOT = ROOT.parent
sys.path.insert(0, str(PILOT))
import run_pilot as pilot


def review():
    out = ROOT / 'verification-001'
    manifest = pilot.load(ROOT / 'manifest.json')
    pilot.require(pilot.sha(out / 'snapshot/manifest.json') == pilot.sha(ROOT / 'manifest.json'), 'Archive manifest drift')
    for name, expected in manifest.items():
        pilot.require(pilot.sha(ROOT/name) == pilot.sha(out/'snapshot'/name) == expected, 'Diagnostic source drift')
    pilot.require(pilot.inventory(PILOT/'model-001') == pilot.load(PILOT/'model-001-sha256.json'), 'Primary archive changed')
    _, tasks, _ = pilot.validate_bundle(PILOT)
    guard = pilot.guard_module(PILOT)
    rows = []
    env = pilot.load(out/'environment.json')
    pilot.require(env['job_id'] == pilot.load(ROOT/'submission.json')['job_id'] and 'login' not in env['host']
                  and env['model_calls'] == 0, 'Compute provenance')
    summary = pilot.load(out/'summary.json')
    cases = pilot.load(ROOT/'cases.json')
    pilot.require(summary['completed_cases'] == len(cases) == 7, 'Incomplete diagnostic')
    for case, record in zip(cases, summary['results']):
        original = PILOT/'model-001'/case['original_trial']
        pilot.require(pilot.sha(original/'response.json') == case['original_response_sha256']
                      and pilot.sha(original/'result.json') == case['original_result_sha256'], 'Response drift')
        text = pilot.load(original/'response.json')['text']
        span = case['extraction']
        extracted = (ROOT/'extracted'/(case['case_id']+'.json')).read_text()
        pilot.require(extracted == text[span['start_char']:span['end_char']], 'Extraction changed proof text')
        task = next(t for t in tasks if t['task_id'] == case['task_id'])
        seeds = pilot.sources(PILOT, task)
        candidate, decision = guard.parse_response(extracted, {n: b.decode() for n,b in seeds.items()}, task)
        pilot.require(decision['candidate_sha256'] == case['candidate_sha256']
                      == pilot.inventory(ROOT/case['path']), 'Candidate changed')
        pilot.require(record == pilot.load(out/(case['case_id']+'.json'))
                      and record['case'] == case and record['model_calls'] == 0, 'Case record mismatch')
        evidence = record['evidence']
        pilot.require(evidence['source_sha256'] == case['candidate_sha256']
                      and evidence['attempts'] == 1 and evidence['model_calls'] == 0, 'Verifier source drift')
        pilot.require(evidence['command'] ==
                      ['timeout','-k','5s','60s','dafny','verify','--verify-included-files','All.dfy'], 'Verifier command')
        rows.append(dict(trial=case['case_id'], task=case['task_id'], outcome=pilot.outcome_for_evidence(evidence),
                         stdout=evidence['stdout'], stderr=evidence['stderr'], exit_code=evidence['exit_code'],
                         candidate_sha256=evidence['source_sha256'], json_sha256=span['json_sha256'],
                         proof_body_edits=False))
    report = dict(job_id=env['job_id'], new_model_calls=0, diagnostic_checks=7,
                  strict_passes=sum(r['outcome']=='VERIFIED' for r in rows),
                  original_pilot_strict_score='1/8', primary_archive_unchanged=True, rows=rows)
    (ROOT/'review.json').write_text(json.dumps(report,indent=2)+'\n')
    (ROOT/'verification-001-sha256.json').write_text(json.dumps(pilot.inventory(out),indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    review()
