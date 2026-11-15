"""Offline D3-M1 path adapter; never modifies its frozen runtime or raw results.

Usage: python -B review_verification.py runtime-001
Writes one fresh reviews/runtime-001/review-001 directory beside this entry point.
"""
from pathlib import Path
from collections import Counter
import hashlib
import importlib.util
import json
import sys

ROOT = Path(__file__).resolve().parent
RUNTIME_SHA256 = '068033e40fc3d8e024481fddec55602ad6c03b41aa783e60d49ad9dc3bd8aad6'
FIXTURE_SHA256 = '8ed7e233c28579fb40e7fbd50eb5cace9ec8d49936b048115028c2f0c29a0dac'
REVIEW_SOURCE = ROOT / 'review-inputs/review_verification.py'
REVIEW_SHA256 = 'f4de7b39772026d86ce92cb825afa45b07a021519d963b234baf1f6e0d8daf2d'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def load(path):
    return json.loads(Path(path).read_text())


def import_file(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


class SnapshotPaths:
    """Route only template lookup and new review outputs; all evidence stays put."""
    def __init__(self, runtime, destination):
        self.runtime, self.destination = Path(runtime), Path(destination)

    def __truediv__(self, name):
        if str(name) in ('templates', 'fixtures'):
            return self.runtime / 'inputs/candidate' / name
        if str(name) in ('results-review.json', 'verification-001-sha256.json'):
            return self.destination / name
        return self.runtime / name


def review(runtime, destination):
    runtime, destination = Path(runtime).resolve(), Path(destination).resolve()
    assert not destination.exists(), 'Do not overwrite a previous review'
    assert not destination.is_relative_to(runtime), 'Review outputs must be outside frozen runtime'
    assert sha(REVIEW_SOURCE.read_bytes()) == REVIEW_SHA256
    assert sha((runtime / 'runtime-manifest.json').read_bytes()) == RUNTIME_SHA256
    assert sha((runtime / 'fixture-manifest.json').read_bytes()) == FIXTURE_SHA256
    pins = {**load(runtime / 'runtime-manifest.json'), **load(runtime / 'fixture-manifest.json')}
    for name, digest in pins.items():
        path = runtime / name
        assert not path.is_symlink() and path.is_file() and sha(path.read_bytes()) == digest, name
    adapter = import_file('intersection_review_pinned_adapter', runtime / 'verify.py')
    assert adapter.validate_pins(runtime) == pins
    upstream = import_file('intersection_review_original', REVIEW_SOURCE)
    out = runtime / 'verification-001'
    inventory = {}
    for path in sorted(out.rglob('*')):
        assert not path.is_symlink(), str(path)
        if path.is_dir():
            continue
        assert path.is_file(), str(path)
        if path != out / 'evidence-manifest.json':
            inventory[path.relative_to(out).as_posix()] = sha(path.read_bytes())
    assert inventory == load(out / 'evidence-manifest.json'), 'Raw evidence inventory mismatch'
    for name, digest in {**pins, 'runtime-manifest.json': RUNTIME_SHA256}.items():
        assert sha((out / name).read_bytes()) == digest, 'Archived input changed: ' + name
    env = load(out / 'environment.json')
    assert env['runtime_manifest_sha256'] == RUNTIME_SHA256
    assert env['fixture_manifest_sha256'] == FIXTURE_SHA256
    for program, expected in [('dafny', adapter.DAFNY_VERSION), ('z3', adapter.Z3_VERSION)]:
        version = env[program]
        assert version['exit_code'] == 0 and version['stdout'].strip() == expected
        assert (out / (program + '-version.stdout')).read_bytes().decode(errors='replace') == version['stdout']
        assert (out / (program + '-version.stderr')).read_bytes().decode(errors='replace') == version['stderr']

    cases = load(runtime / 'cases.json')
    summary = load(out / 'summary.json')
    assert [r['case_id'] for r in summary['checks']] == [c['case_id'] for c in cases]
    strict = {}
    for case, summary_row in zip(cases, summary['checks']):
        path = out / (case['case_id'] + '.json')
        ev = load(path)
        category, matched = adapter.classify(ev), adapter.matches(case, ev)
        assert ev['case_id'] == case['case_id']
        assert ev['actual'] == summary_row['actual'] == category
        assert ev['matched'] == summary_row['matched'] == matched
        assert ev['expected'] == summary_row['expected'] == case['expected']
        assert ev['expected_diagnostic'] == summary_row['expected_diagnostic'] == case['expected_diagnostic']
        assert summary_row['evidence_sha256'] == sha(path.read_bytes())
        strict[case['case_id']] = dict(strict_actual=category, strict_expected_match=matched,
                                     strict_expected_exit=case['expected_exit'], actual_exit=ev['exit_code'])
    assert summary['all_expected'] == all(row['strict_expected_match'] for row in strict.values())

    destination.mkdir(parents=True, exist_ok=False)
    # Original reviewer retains all provider/client/body-boundary, named-scope,
    # raw/base64/CSV and primary-error-location checks. No fixture is copied back.
    result = upstream.review(SnapshotPaths(runtime, destination))
    for row in result['checks']:
        row.update(strict[row['case_id']])
        row['matched'] = row['matched'] and row['strict_expected_match']
    result['all_expected'] = all(row['matched'] for row in result['checks'])
    result['strict_counts'] = dict(Counter(row['strict_actual'] for row in result['checks']))
    result['expected_counts'] = dict(Counter(case['expected'] for case in cases))
    result.update(runtime_manifest_sha256=RUNTIME_SHA256, fixture_manifest_sha256=FIXTURE_SHA256,
                  original_reviewer_sha256=REVIEW_SHA256, archived_input_files_checked=len(pins) + 1,
                  raw_inventory_files_checked=len(inventory),
                  path_adaptation='templates/fixtures resolve under inputs/candidate; reports are outside runtime',
                  claim='Verifier-only development controls for ghost interval certificates; no model, executable-search, held-out, minimum-depth or causal-sharing claim')
    (destination / 'results-review.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('all_expected', 'counts', 'strict_counts', 'expected_counts',
                                           'protected_file_comparisons', 'protected_body_boundaries')}, indent=2))
    return result


if __name__ == '__main__':
    assert sys.argv[1:] == ['runtime-001'], 'Specify the one pinned runtime-001'
    result = review(ROOT / 'runtime-001', ROOT / 'reviews/runtime-001/review-001')
    raise SystemExit(0 if result['all_expected'] else 1)
