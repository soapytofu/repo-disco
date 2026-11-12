"""Analyst-only call-order diagnostic; never changes or rescores model archives."""
import hashlib
import json
from pathlib import Path
import body_guard

ROOT=Path(__file__).resolve().parent
CERT='O1.Certify(K.Restrict(m, keep), K.Restrict(n, keep));'
FACT='O2.RestrictKeys(n, keep);'
TWO=('ensures key0 in K.Merge(K.Restrict(m, keep), K.Restrict(n, keep))\n'
     '      ensures K.Restrict(K.Merge(m, n), keep)[key0] == K.Merge(K.Restrict(m, keep), K.Restrict(n, keep))[key0]')
ONE=TWO.replace('\n      ensures ',' && ')

def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def files(p):return {x.name:x.read_text() for x in p.glob('*.dfy')}
def hashes(fs):return {n:hashlib.sha256(s.encode()).hexdigest() for n,s in fs.items()}

def reorder(body):
    lines=body.splitlines(keepends=True)
    i=[i for i,s in enumerate(lines) if s.strip()==CERT]
    j=[i for i,s in enumerate(lines) if s.strip()==FACT]
    assert len(i)==len(j)==1 and i[0]<j[0]
    line=lines.pop(i[0]);j=next(i for i,s in enumerate(lines) if s.strip()==FACT)
    lines.insert(j+1,line)
    return ''.join(lines)

def review_syntax(body,task,originally_rejected):
    projection=body
    if originally_rejected:
        assert body.count(TWO)==1
        # Only for syntax review. Both actual ensures clauses stay in Dafny input.
        projection=body.replace(TWO,ONE)
    parser=body_guard.Grammar(projection,task);parser.sequence();assert parser.peek() is None

def candidates():
    rows=[]
    for tid,repaired in [('map-dev-04',False),('map-dev-04',True),('map-dev-08',True),('map-dev-09',True)]:
        task=load(ROOT/'parents'/tid/'task.json')
        response=load(ROOT/'parents'/tid/'response.json')
        bodies=json.loads(response['text']);seed=files(ROOT/'seeds'/tid)
        assert set(bodies)==set(task['editable_files'])
        original=dict(seed);candidate=dict(seed)
        for name,body in bodies.items():
            prefix,suffix=body_guard.split_seed(seed[name])
            original[name]=prefix+body+suffix
            edited=reorder(body) if repaired else body
            review_syntax(edited,task,tid=='map-dev-04')
            candidate[name]=prefix+edited+suffix
        if tid!='map-dev-04':
            assert original==files(ROOT/'parents'/tid/'candidate')
            assert hashes(original)==load(ROOT/'parents'/tid/'verification.json')['source_sha256']
        cid=tid+('-reordered' if repaired else '-original-unadmitted')
        rows.append((dict(case_id=cid,parent_trial=tid,path='fixtures/'+cid,
            expected_exit=0 if repaired else 4,expected_diagnostic='success' if repaired else 'precondition_failure',
            source_sha256=hashes(candidate),parent_source_sha256=hashes(original),
            original_body_policy_admitted=tid!='map-dev-04',analyst_only=True,
            change='Move one existing certificate call after both restriction-key facts' if repaired else 'No source change; trusted analyst check of originally unadmitted body',
            model_calls=0),candidate))
    return rows

def write():
    out=ROOT/'fixtures';out.mkdir(exist_ok=False);cases=[]
    for row,fs in candidates():
        dest=ROOT/row['path'];dest.mkdir()
        for n,s in fs.items():(dest/n).write_text(s)
        cases.append(row)
    (ROOT/'cases.json').write_text(json.dumps(cases,indent=2)+'\n')

if __name__=='__main__':write()
