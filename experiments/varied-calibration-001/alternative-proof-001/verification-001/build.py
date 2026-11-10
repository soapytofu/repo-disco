"""Analyst alternatives under the existing contracts/guard; not model outputs."""
import hashlib,json
from pathlib import Path
import task_definition as definition
import body_guard as guard
import extract_response
ROOT=Path(__file__).resolve().parent

def alternative(instance,depth):
    if instance=='bounded_allocation':
        return definition.allocation(depth,'reference').replace('if a >= t-d then a else t-d','if b <= t-c then b else t-c')
    if instance=='map_swap':
        head='    var once := K.Swap(m,k,j);\n    var twice := K.Swap(once,k,j);\n    if k==j {\n'
        if depth=='shallow':head+='      A.ObserveSwap(m,k,j);\n'
        else:head+='''      O1.Certify(m,k,j); O2.SwapKeys(m,k,j);
      forall q | q in m ensures q in once && m[q]==once[q] {
        O2.SwapAt(m,k,j,q);
      }
'''
        head+='''      A.Equal(m,once);
      assert twice==m;
    } else {
'''
        if depth=='shallow':head+='      A.ObserveSwap(m,k,j); A.ObserveSwap(once,k,j);\n'
        else:head+='''      O1.Certify(m,k,j); O2.SwapKeys(m,k,j);
      O1.Certify(once,k,j); O2.SwapKeys(once,k,j);
'''
        head+='      forall q | q in m ensures q in twice && m[q]==twice[q] {\n'
        if depth=='deep':head+='''        if q==k { O2.SwapAt(m,k,j,j); }
        else if q==j { O2.SwapAt(m,k,j,k); }
        else { O2.SwapAt(m,k,j,q); }
        O2.SwapAt(once,k,j,q);
'''
        return head+'      }\n      A.Equal(m,twice);\n    }\n'
    if instance=='clamp_distance':
        def call(c,x):return f'A.{c}(l,h,{x});' if depth=='shallow' else f'O1.{c}(l,h,{x}); O2.Read{c}(l,h,{x});'
        body=''
        for x in ['y','x']:
            body+=f'    if {x}>h {{ {call("Above",x)} }}\n    else if {x}<l {{ {call("Below",x)} }}\n    else {{ {call("Within",x)} }}\n'
        return body
    if instance=='prefix_split':
        def obs(s,n):return f'A.Observe({s},{n});' if depth=='shallow' else f'O1.Unfold({s},{n}); O2.Expose({s},{n});'
        return f'''    if j==0 {{
      {obs('s[i..]','0')}
    }} else if i==0 {{
      {obs('s','0')}
      assert s[0..]==s;
    }} else {{
      Prove(s[1..],i-1,j);
      {obs('s','i')}
      {obs('s','i+j')}
      assert (s[1..])[i-1..]==s[i..];
    }}
'''
    raise ValueError(instance)

def build():
    parent=ROOT.parent/'revision-002';tasks=json.loads((parent/'tasks.json').read_text());checks=[]
    (ROOT/'tasks.json').write_bytes((parent/'tasks.json').read_bytes())
    for t in tasks:
        tid=t['task_id'];seed=definition.sources(t['semantic_instance'],t['depth'],t['sharing'],'empty')
        body='\n'+alternative(t['semantic_instance'],t['depth'])
        payload={n:body for n in t['editable_files']}
        raw='An analyst alternative follows.\n```json\n'+json.dumps(payload,indent=2)+'\n```\n'
        candidate,decision=extract_response.parse_response(raw,seed,t,guard)
        dest=ROOT/'fixtures'/tid/'alternative';dest.mkdir(parents=True,exist_ok=False)
        for n,s in candidate.items():(dest/n).write_text(s)
        resp=ROOT/'responses'/tid;resp.mkdir(parents=True,exist_ok=False)
        (resp/'response.txt').write_text(raw);(resp/'extraction.json').write_text(json.dumps(decision,indent=2)+'\n')
        checks.append(dict(task_id=tid,variant='alternative',path=str(dest.relative_to(ROOT)),phase='core',expected='success',source_sha256=definition.hashes(candidate)))
    (ROOT/'checks.json').write_text(json.dumps(checks,indent=2)+'\n')
    print(json.dumps(dict(analyst_candidates=len(checks),new_model_calls=0)))

if __name__=='__main__':build()
