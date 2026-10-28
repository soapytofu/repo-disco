"""Offline audit of completed scripted agent controls; no verifier/model calls."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'verification-001'
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def files(p):return {str(f.relative_to(p)):f.read_bytes() for f in p.rglob('*.dfy')}
def hashes(fs):return {k:hashlib.sha256(v).hexdigest() for k,v in sorted(fs.items())}

def main():
    pinned=load(ROOT/'manifest-sha256.json');checked=[]
    for name,digest in pinned.items():
        if name.startswith(('code/','guards/','fixtures/')) or name=='run_controls.py':
            assert sha(OUT/name)==digest,name
            checked.append(name)
    env=load(OUT/'environment.json');assert env['model_calls']==0 and env['response_mode']=='scripted_saved_fixtures'
    rows=[];verifier_checks=0
    for family in ['inductive','branch']:
        for condition in ['shared','separate']:
            name=family+'-'+condition;store=OUT/name/'store'
            positive=files(ROOT/'fixtures'/family/(condition+'_reference'))
            empty=files(ROOT/'fixtures'/family/(condition+'_empty'))
            negative=files(ROOT/'fixtures'/family/(condition+('_no_recursive_step' if family=='inductive' else '_wrong_boundary')))
            head=load(store/'HEAD.json')['revision'];accepted=load(store/'revisions'/head/'revision.json');base=accepted['parent']
            assert files(store/'revisions'/head/'files')==positive
            assert files(store/'revisions'/base/'files')==empty
            assert accepted['source_sha256']==hashes(positive)
            assert accepted['verification']['exit_code']==0
            assert accepted['verification']['source_sha256']==hashes(positive)
            assert len(list((store/'revisions').iterdir()))==2
            initial=load(store/('initial-verification-'+base+'.json'))
            assert initial['exit_code']==4 and initial['category']=='proof_failure'
            assert initial['source_sha256']==hashes(empty);verifier_checks+=1
            ledger=load(OUT/name/'request-ledger/ledger.json');requests=ledger['reservations']
            assert ledger['limit']==3 and len(requests)==3
            expected=['EDIT_REJECTED','PROOF_FAILURE','SUCCESS'];diagnostics=[]
            for i,r in enumerate(requests):
                assert r['status']=='COMPLETED'
                attempt=store/'attempts'/r['attempt_id'];result=load(attempt/'result.json');ctx=load(attempt/'context.json')
                assert result['outcome']==expected[i] and ctx==r['prompt']
                assert ctx['files']=={k:v.decode() for k,v in sorted(empty.items())}
                assert load(attempt/'response.json')==load(OUT/name/'request-ledger'/('response-%03d.json'%(i+1)))
                if i==0:assert not (attempt/'verification.json').exists()
                else:
                    evidence=load(attempt/'verification.json');candidate=files(attempt/'candidate')
                    assert candidate==(negative if i==1 else positive)
                    assert evidence['source_sha256']==hashes(candidate)
                    assert evidence['exit_code']==(4 if i==1 else 0)
                    assert evidence['category']==('proof_failure' if i==1 else 'success')
                    assert '--verify-included-files' in evidence['command']
                    if i==1:
                        assert any(t in evidence['stdout'].lower() for t in ['assertion','postcondition','precondition'])
                        assert 'parse errors' not in evidence['stdout'].lower()
                    diagnostics.append(dict(outcome=expected[i],exit_code=evidence['exit_code'],category=evidence['category']))
                    verifier_checks+=1
                if i==2:assert ctx['feedback']['outcome']=='PROOF_FAILURE'
            rows.append(dict(case=name,outcomes=expected,original_revision_preserved=True,
                             accepted_exact_reference=True,verification=diagnostics))
    assert verifier_checks==12
    return dict(all_expected=True,expected_cases=4,verifier_checks=12,guard_rejections=4,
                actual_model_calls=0,scripted_requests=12,pinned_files_checked=len(checked),
                cases=rows,source_summary_sha256=sha(OUT/'summary.json'))

if __name__=='__main__':
    result=main();(ROOT/'control-review.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
