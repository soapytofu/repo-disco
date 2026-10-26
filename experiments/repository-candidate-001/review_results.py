"""Offline integrity and diagnostic review. No verifier or model execution."""
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parent
run=ROOT/'verification-001'
def tree(root):
    return {str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file() and '__pycache__' not in str(p)}
def hashes(files): return {k:hashlib.sha256(v).hexdigest() for k,v in files.items()}
def files(path): return {p.name:p.read_bytes() for p in path.glob('*.dfy')}
for name in ['code','guards','fixtures']: assert tree(run/name)==tree(ROOT/name),name
assert (run/'run_integration.py').read_bytes()==(ROOT/'run_integration.py').read_bytes()
for name in tree(ROOT/'code'):
    assert (ROOT/'code'/name).read_bytes()==(ROOT.parents[1]/name).read_bytes(),name
for task,names in [('inductive-sharing-001',['provider_guard.py','provider_payload.py']),('sharing-branching-001',['branch_guard.py','json_payload.py'])]:
    for name in names: assert (ROOT/'guards'/name).read_bytes()==(ROOT.parent/task/name).read_bytes()
rows=[]
for family in ['inductive','branch']:
    original=ROOT.parent/('inductive-sharing-001/revision-003/fixtures' if family=='inductive' else 'sharing-branching-001/fixtures')
    for condition in ['shared','separate']:
        base=files(run/'fixtures'/family/(condition+'_empty'))
        assert base==files(original/(condition+'_empty'))
        for variant in ['reference','no_recursive_step' if family=='inductive' else 'wrong_boundary']:
            label=family+'-'+condition+'-'+variant
            report=json.loads((run/(label+'.json')).read_text())
            candidate=files(run/'fixtures'/family/(condition+'_'+variant))
            assert candidate==files(original/(condition+'_'+variant))
            assert report['source_sha256']==hashes(candidate)
            assert report['candidate']['base_sha256']==hashes(base)
            changed=sorted(k for k in base if base[k]!=candidate[k])
            assert report['candidate']['changed_files']==changed
            assert changed==(['Facts.dfy'] if family=='inductive' else ['ClientA.dfy','ClientB.dfy'])
            assert report['candidate']['promoted'] is False and report['agenda_bytes_unchanged']
            expected=0 if variant=='reference' else 4
            assert report['exit_code']==report['expected_exit']==expected
            assert report['attempts']==1 and report['model_calls']==0
            assert report['stderr']==''
            summary=re.search(r'(\d+) verified, (\d+) errors?',report['stdout'])
            assert summary and (int(summary[2])==0 if expected==0 else int(summary[2])>0)
            if expected==4:
                assert any(x in report['stdout'] for x in ['postcondition could not be proved','assertion might not hold','a precondition for this call could not be proved'])
                assert 'parse error' not in report['stdout'] and 'resolution/type errors' not in report['stdout']
            rows.append(dict(case=label,exit_code=expected,verified=int(summary[1]),errors=int(summary[2]),changed_files=changed))
reject=json.loads((run/'guard-rejections.json').read_text())
assert len(reject)==4 and len({(r['family'],r['condition']) for r in reject})==4
assert all(r['verifier_calls']==0 and 'Protected' in r['reason'] for r in reject)
result=dict(job_id='55310512',matched=8,guard_rejections=4,exact_source_code_guard_hashes_reviewed=True,
            model_calls=0,checks=rows,limitation='Integration evidence, not model performance; no agenda promotion tested')
(ROOT/'review.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
