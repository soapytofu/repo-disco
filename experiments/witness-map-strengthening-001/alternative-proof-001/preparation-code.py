"""New proof strategies through the pinned envelope+guard; no model/Dafny calls."""
import hashlib,importlib.util,json,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'alternative-proof-001'
sys.path.insert(0,str(ROOT/'protocol'));sys.path.insert(0,str(ROOT.parent/'reasoning-envelope-policy-001'))
import body_guard,extract_response
sha=lambda b:hashlib.sha256(b).hexdigest()
def witness(depth):
 s='    var v := if b <= d then b else d;\n    var u := v - gap;\n'
 if depth=='shallow':return s+'    A.Direct(a,b,c,d,gap,u,v);\n'
 return s+'''    O1.Right(c,d,v); O1.Left(a,b,v); O2.Join(a,b,c,d,v);
    O1.Separate(u,v,gap);
    O1.Right(c,d,u); O1.Left(a,b,u); O2.Join(a,b,c,d,u);
    A.Finish(a,b,c,d,gap,u,v);
'''
def mapping(depth):
 s='''    var u := K.Put(m,k,x);
    var v := K.Put(u,j,y);
    var base := K.Drop(m,k);
    var left := K.Drop(v,k);
    var right := if k == j then base else K.Put(base,j,y);
'''
 if depth=='shallow':s+='''    A.ObserveDrop(m,k); A.ObservePut(m,k,x);
    A.ObservePut(u,j,y); A.ObserveDrop(v,k);
    if j != k { A.ObservePut(base,j,y); }
'''
 else:s+='''    O1.DropKeys(m,k); O1.PutKeys(m,k,x);
    O1.PutKeys(u,j,y); O1.DropKeys(v,k);
    if j != k { O1.PutKeys(base,j,y); }
'''
 s+='''    assert left.Keys == right.Keys;
    forall q | q in left ensures q in right && left[q] == right[q] {
'''
 if depth=='deep':s+='''      O2.DropAt(v,k,q); O2.PutAt(u,j,y,q);
      if q == j {
        assert j != k;
        O2.PutAt(base,j,y,q);
      } else {
        O2.PutAt(m,k,x,q); O2.DropAt(m,k,q);
        if j != k { O2.PutAt(base,j,y,q); }
      }
'''
 else:s+='''      if q == j { assert j != k; } else { assert q in m; }
'''
 return s+'''    }
    A.Equal(left,right);
'''

def main():
 OUT.mkdir(exist_ok=False);tasks=json.loads((ROOT/'tasks.json').read_text());checks=[];decisions=[]
 for t in tasks:
  seeds={p.name:p.read_text() for p in (ROOT/'fixtures'/t['task_id']/'empty').glob('*.dfy')}
  seedout=OUT/'seeds'/t['task_id'];seedout.mkdir(parents=True)
  for n,s in seeds.items():(seedout/n).write_text(s)
  b=witness(t['depth']) if t['semantic_instance']=='separated_witness' else mapping(t['depth'])
  payload={n:b for n in t['editable_files']};raw='An alternative proof strategy follows.\n```json\n'+json.dumps(payload)+'\n```\nThe immutable interfaces remain unchanged.'
  files,decision=extract_response.parse_response(raw,seeds,t,body_guard)
  target=OUT/'fixtures'/t['task_id'];target.mkdir(parents=True)
  for n,s in files.items():(target/n).write_text(s)
  response=OUT/'responses'/t['task_id'];response.mkdir(parents=True)
  (response/'response.txt').write_text(raw);(response/'decision.json').write_text(json.dumps(decision,indent=2)+'\n')
  checks.append(dict(task_id=t['task_id'],variant='alternative',path=str(target.relative_to(OUT)),expected='success',source_sha256={n:sha(s.encode()) for n,s in files.items()}))
  decisions.append(dict(task_id=t['task_id'],strategy='upper endpoint minus gap' if t['semantic_instance']=='separated_witness' else 'query-key case split and reversed key comparison',parent_sha256=t['source_sha256'],candidate_sha256=checks[-1]['source_sha256'],raw_response_sha256=sha(raw.encode()),analyst_authored=True,model_calls=0))
 for name,data in [('checks.json',checks),('tasks.json',tasks),('preparation.json',decisions)]:
  (OUT/name).write_text(json.dumps(data,indent=2)+'\n')
 for name in ['preflight.py','review.py']:
  s=(ROOT/name).read_text().replace('len(checks)!=64','len(checks)!=8').replace('fixed 64 controls','fixed 8 controls');(OUT/name).write_text(s)
 shutil.copytree(ROOT/'code',OUT/'code')
 shutil.copy2(ROOT/'protocol/body_guard.py',OUT/'body_guard.py');shutil.copy2(ROOT.parent/'reasoning-envelope-policy-001/extract_response.py',OUT/'extract_response.py')
 shutil.copy2(Path(__file__),OUT/'preparation-code.py')
 script=(ROOT/'verify.sbatch').read_text().replace('witness-map-verify','witness-map-alt').replace('00:20:00','00:10:00').replace('outputs/witness-map-strengthening-001','outputs/witness-map-strengthening-001/alternative-proof-001')
 (OUT/'verify.sbatch').write_text(script)
 # Reuse bounded verifier operations; remote offline preflight uses the exact round-trip test below.
 ops=(ROOT/'ops.py').read_text().replace("REMOTE='formal-disco/outputs/witness-map-strengthening-001'","REMOTE='formal-disco/outputs/witness-map-strengthening-001/alternative-proof-001'").replace('witness-map-verify','witness-map-alt')
 (OUT/'ops.py').write_text(ops)
 print(json.dumps(dict(alternatives=len(checks),model_calls=0,verification_pending=True)))
if __name__=='__main__':main()
