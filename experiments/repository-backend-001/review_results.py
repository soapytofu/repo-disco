"""Offline review of the compute integration evidence; no verifier/model calls."""
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
run = ROOT/'verification-001'
review = []
for part in ['code', 'fixtures']:
    expected = {str(p.relative_to(ROOT/part)):p.read_bytes() for p in (ROOT/part).rglob('*') if p.is_file() and '__pycache__' not in str(p)}
    actual = {str(p.relative_to(run/part)):p.read_bytes() for p in (run/part).rglob('*') if p.is_file() and '__pycache__' not in str(p)}
    assert actual == expected, part
assert (run/'run_integration.py').read_bytes() == (ROOT/'run_integration.py').read_bytes()
for variant in ['shared_reference','shared_empty','separate_reference','separate_empty']:
    report = json.loads((run/(variant+'.json')).read_text())
    source = {p.name:p.read_bytes() for p in (run/'fixtures'/variant).glob('*.dfy')}
    original = ROOT.parent/'inductive-sharing-001'/'revision-003'/'fixtures'/variant
    assert source == {p.name:p.read_bytes() for p in original.glob('*.dfy')}
    assert report['source_sha256'] == {k:hashlib.sha256(v).hexdigest() for k,v in source.items()}
    expected = 0 if variant.endswith('reference') else 4
    assert report['exit_code'] == report['expected_exit'] == expected
    assert report['attempts'] == 1 and report['model_calls'] == 0
    assert report['agenda_bytes_unchanged']
    assert report['stderr'] == ''
    summary = re.search(r'(\d+) verified, (\d+) errors?', report['stdout'])
    assert summary and (int(summary[2]) == 0 if expected == 0 else int(summary[2]) > 0)
    if expected == 4:
        assert 'a postcondition could not be proved' in report['stdout']
        assert 'parse error' not in report['stdout'] and 'resolution/type errors' not in report['stdout']
    review.append(dict(variant=variant,exit_code=expected,verified=int(summary[1]),errors=int(summary[2]),
                       category=report['category'],source_hashes_match=True,original_fixture_bytes_match=True))
result = dict(job_id='55308603',checks=review,code_snapshot_matches=True,runner_matches=True,
              matched=4,model_calls=0,interpretation='Integration control outcomes; not model performance or baseline reproduction')
(ROOT/'review.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
