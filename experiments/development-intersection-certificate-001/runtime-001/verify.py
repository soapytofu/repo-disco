"""Compute-only adapter around the exact archived witness verifier; no providers."""
from pathlib import Path, PurePosixPath
import hashlib
import importlib.util
import json
import re
import sys

ROOT = Path(__file__).resolve().parent
CANDIDATE_SHA256 = 'b7399a81a95de0471811c3808360a3c3ff5f109e2bc63fa38468db1d61d4ed91'
UPSTREAM = 'inputs/candidate/inputs/experiments/repair-diversity-expansion-001/witness/verify.py'
UPSTREAM_SHA256 = '4f29cefb7bba9b44287e4cb028cc55b9ebf1b11a6be37cae86c9405ae68935f9'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def load(path):
    return json.loads(Path(path).read_text())


def checked_path(root, name):
    rel = PurePosixPath(name)
    assert isinstance(name, str) and rel.parts and str(rel) == name
    assert not rel.is_absolute() and '..' not in rel.parts, name
    path = Path(root)
    assert not path.is_symlink(), str(path)
    for component in rel.parts:
        path /= component
        assert not path.is_symlink(), name
    assert path.is_file() and path.resolve().is_relative_to(Path(root).resolve()), name
    return path


assert sha(checked_path(ROOT, UPSTREAM).read_bytes()) == UPSTREAM_SHA256
_spec = importlib.util.spec_from_file_location('intersection_archived_witness_verifier', ROOT / UPSTREAM)
upstream = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(upstream)


def validate_pins(root=None):
    """Validate flat staging pins and the complete immutable candidate snapshot."""
    root = Path(ROOT if root is None else root)
    runtime = load(checked_path(root, 'runtime-manifest.json'))
    fixtures = load(checked_path(root, 'fixture-manifest.json'))
    assert runtime and fixtures
    required = {'README.md', 'verify.py', 'verify.sbatch', 'test_structure.py',
                'adapter-preservation-001.json', 'fixture-manifest.json'}
    assert required <= set(runtime)
    allpins = {}
    for manifest in (runtime, fixtures):
        for name, digest in manifest.items():
            assert isinstance(digest, str) and re.fullmatch('[0-9a-f]{64}', digest), name
            assert name not in allpins or allpins[name] == digest, name
            assert sha(checked_path(root, name).read_bytes()) == digest, name
            allpins[name] = digest

    prefix = 'inputs/candidate/'
    snapshot = root / 'inputs/candidate'
    original_manifest = checked_path(root, prefix + 'candidate-manifest.json')
    assert sha(original_manifest.read_bytes()) == CANDIDATE_SHA256
    original = load(original_manifest)['files_sha256']
    snapshot_pins = {**original, 'candidate-manifest.json': CANDIDATE_SHA256}
    observed = {}
    for path in sorted(snapshot.rglob('*')):
        assert not path.is_symlink(), str(path)
        if path.is_dir():
            continue
        assert path.is_file(), str(path)
        observed[path.relative_to(snapshot).as_posix()] = sha(path.read_bytes())
    assert observed == snapshot_pins, 'Candidate snapshot differs from original inventory'
    assert sha(checked_path(root, UPSTREAM).read_bytes()) == UPSTREAM_SHA256

    original_cases = load(snapshot / 'cases.json')
    cases = load(root / 'cases.json')
    expected_cases = [dict(case, path=prefix + case['path']) for case in original_cases]
    assert cases == expected_cases, 'Only case paths may be mechanically prefixed'
    assert (root / 'tasks.json').read_bytes() == (snapshot / 'tasks.json').read_bytes()
    expected_fixtures = {prefix + name: digest for name, digest in snapshot_pins.items()}
    expected_fixtures.update({name: sha((root / name).read_bytes()) for name in ('cases.json', 'tasks.json')})
    assert fixtures == expected_fixtures, 'Unexpected flat fixture inventory'
    assert len(cases) == 20 and len({case['case_id'] for case in cases}) == 20
    assert {status: sum(case['expected'] == status for case in cases)
            for status in ('success', 'proof_failure', 'resolution_failure')} == {
                'success': 4, 'proof_failure': 14, 'resolution_failure': 2}
    for case in cases:
        folder = root / case['path']
        source_hashes = {path.name: sha(path.read_bytes()) for path in sorted(folder.glob('*.dfy'))}
        assert source_hashes == case['source_sha256'], case['case_id']
        assert case['expected_diagnostic'] in ('none', *upstream.DIAGNOSTICS)
        assert case['entry'] == 'All.dfy'
        for name, digest in source_hashes.items():
            assert fixtures[case['path'] + '/' + name] == digest
    metadata = load(root / 'adapter-preservation-001.json')
    assert metadata['candidate_manifest_sha256'] == CANDIDATE_SHA256
    assert metadata['upstream_wrapper_sha256'] == UPSTREAM_SHA256
    assert metadata['planned_checks'] == 20 and metadata['model_calls'] == 0
    return allpins


# The original run loop, raw-byte capture, version checks and diagnostic matcher
# are reused unchanged. Its globals are explicitly rooted in this isolated bundle.
upstream.ROOT = ROOT
upstream.validate_pins = validate_pins
run = upstream.run
verify = upstream.verify
matches = upstream.matches
classify = upstream.classify
diagnostic_details = upstream.diagnostic_details
COMMAND = upstream.COMMAND
DAFNY_VERSION = upstream.DAFNY_VERSION
Z3_VERSION = upstream.Z3_VERSION


if __name__ == '__main__':
    assert len(sys.argv) == 2, 'Specify verification-001'
    raise SystemExit(0 if run(sys.argv[1]) else 1)
