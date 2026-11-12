"""Move one existing prerequisite-dependent call; never edit model evidence."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import body_guard
import extract_response

ROOT=Path(__file__).resolve().parent
CERT='O1.Certify(K.Restrict(m, keep), K.Restrict(n, keep));'
FACTS=('O2.RestrictKeys(m, keep);','O2.RestrictKeys(n, keep);')

def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def files(p):return {x.name:x.read_text() for x in p.glob('*.dfy')}
def hashes(fs):return {n:hashlib.sha256(s.encode()).hexdigest() for n,s in fs.items()}

def reorder(body):
    lines=body.splitlines(keepends=True)
    positions={text:[i for i,line in enumerate(lines) if line.strip()==text] for text in (CERT,*FACTS)}
    assert all(len(xs)==1 for xs in positions.values()),'Expected exactly one of each fixed call'
    assert positions[CERT][0]<min(positions[f][0] for f in FACTS),'Original certificate is not early'
    line=lines.pop(positions[CERT][0])
    last=max(i for i,s in enumerate(lines) if s.strip() in FACTS)
    lines.insert(last+1,line)
    result=''.join(lines)
    assert Counter(result.splitlines(keepends=True))==Counter(body.splitlines(keepends=True))
    return result

def candidates():
    rows=[]
    for tid in load(ROOT/'provenance.json')['parent_trials']:
        parent=ROOT/'parents'/tid;task=load(parent/'task.json');response=load(parent/'response.json')
        seed=files(ROOT/'seeds'/tid)
        original,decision=extract_response.parse_response(response['text'],seed,task,body_guard)
        assert dict(accepted=True,**decision)==load(parent/'extraction.json')
        assert original==files(parent/'candidate')
        evidence=load(parent/'verification.json')
        assert evidence['exit_code']==4 and hashes(original)==evidence['source_sha256']
        assert task['semantic_instance']=='merge_restrict' and task['depth']=='deep'
        bodies={}
        for name in task['editable_files']:
            prefix,suffix=body_guard.split_seed(seed[name])
            bodies[name]=reorder(original[name][len(prefix):-len(suffix)])
        candidate,_=extract_response.parse_response(json.dumps(bodies),seed,task,body_guard)
        cid=tid+'-reordered'
        rows.append((dict(case_id=cid,parent_trial=tid,path='fixtures/'+cid,
            expected_exit=0,expected_diagnostic='strict_success',source_sha256=hashes(candidate),
            parent_source_sha256=hashes(original),original_body_policy_admitted=True,
            analyst_only=True,model_calls=0,edited_bodies=len(bodies),
            change='Move the existing restricted-map certificate call after both RestrictKeys calls; no other changes'),candidate))
    return rows

def write():
    (ROOT/'fixtures').mkdir(exist_ok=False);cases=[]
    for row,fs in candidates():
        dest=ROOT/row['path'];dest.mkdir()
        for n,s in fs.items():(dest/n).write_text(s)
        cases.append(row)
    (ROOT/'cases.json').write_text(json.dumps(cases,indent=2)+'\n')

if __name__=='__main__':write()
