"""D4-M1 development construction only; no model or verifier dispatch."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent

KERNEL='''module Kernel {
  export Public provides Move, Ready
  export Internal reveals Move, Ready
  opaque predicate Ready(m: map<int,int>,a: int,b: int) {
    a in m && b !in m && a != b
  }
  opaque function Move(m: map<int,int>,a: int,b: int): map<int,int> {
    if a in m && b !in m && a != b then
      (map q | q in m && q != a :: m[q])[b := m[a]]
    else m
  }
}
'''
OPS1='''include "Kernel.dfy"
module Ops1 {
  export Hidden provides K
  export Public provides K, Certify
  import K = Kernel`Internal
  lemma Certify(m: map<int,int>,a: int,b: int)
    requires a in m && b !in m && a != b
    ensures K.Ready(m,a,b)
  { reveal K.Ready(); }
}
'''
OPS2='''include "Kernel.dfy"
module Ops2 {
  export Hidden provides K
  export Public provides K, MoveKeys, MoveAt
  import K = Kernel`Internal
  lemma MoveKeys(m: map<int,int>,a: int,b: int)
    requires K.Ready(m,a,b)
    ensures K.Move(m,a,b).Keys == (m.Keys - {a}) + {b}
  { reveal K.Ready(); reveal K.Move(); }
  lemma MoveAt(m: map<int,int>,a: int,b: int,q: int)
    requires a in m && b !in m && a != b
    requires K.Ready(m,a,b)
    requires q == b || (q in m && q != a)
    ensures q in K.Move(m,a,b)
    ensures K.Move(m,a,b)[q] == (if q == b then m[a] else m[q])
  { reveal K.Move(); }
}
'''
API='''include "Kernel.dfy"
module Api {
  export Shallow provides K, ObserveMove, Equal
  export Deep provides K, Equal
  import K = Kernel`Internal
  lemma ObserveMove(m: map<int,int>,a: int,b: int)
    requires a in m && b !in m && a != b
    ensures K.Move(m,a,b).Keys == (m.Keys - {a}) + {b}
    ensures forall q :: q in K.Move(m,a,b) ==>
      K.Move(m,a,b)[q] == (if q == b then m[a] else m[q])
  { reveal K.Move(); }
  lemma Equal(left: map<int,int>,right: map<int,int>)
    requires left.Keys == right.Keys
    requires forall q :: q in left ==> q in right && left[q] == right[q]
    ensures left == right
  { }
}
'''
SIGNATURE='''  lemma {:induction false} Prove(m: map<int,int>,a: int,b: int,c: int)
    requires a in m && b !in m && c !in m
    requires a != b && b != c && a != c
    ensures K.Move(K.Move(m,a,b),b,c) == K.Move(m,a,c)
'''
VARIANTS=['reference','empty','missing_inner_value','stale_snapshot','keep_intermediate',
          'lost_value','skip_singleton','occupied_destination','hidden_shortcut']

def hashes(fs):return {n:hashlib.sha256(s.encode()).hexdigest() for n,s in sorted(fs.items())}

def proof(depth,variant):
    if variant=='empty':return ''
    if variant=='hidden_shortcut':
        return '    O1.Certify(m,a,b);\n' if depth=='shallow' else '    A.ObserveMove(m,a,b);\n'
    body='''    var mid := K.Move(m,a,b);
    var left := K.Move(mid,b,c);
    var right := K.Move(m,a,c);
'''
    if depth=='shallow':
        body+='''    A.ObserveMove(m,a,b);
    A.ObserveMove(mid,b,c);
    A.ObserveMove(m,a,c);
'''
    else:
        body+='''    O1.Certify(m,a,b); O2.MoveKeys(m,a,b);
    O1.Certify(mid,b,c); O2.MoveKeys(mid,b,c);
    O1.Certify(m,a,c); O2.MoveKeys(m,a,c);
'''
    body+='''    assert left.Keys == right.Keys;
    forall q | q in left ensures q in right && left[q] == right[q] {
'''
    if depth=='deep':
        body+='''      O2.MoveAt(mid,b,c,q);
      O2.MoveAt(m,a,c,q);
      if q == c { O2.MoveAt(m,a,b,b); }
      else { O2.MoveAt(m,a,b,q); }
'''
    body+='''    }
    A.Equal(left,right);
'''
    if variant=='missing_inner_value':
        body=body.replace('O2.MoveAt(m,a,b,b);','') if depth=='deep' else body.replace('    A.ObserveMove(m,a,b);\n','')
    elif variant=='stale_snapshot':
        body=body.replace('O2.MoveAt(mid,b,c,q);','O2.MoveAt(m,b,c,q);') if depth=='deep' else body.replace('A.ObserveMove(mid,b,c);','A.ObserveMove(m,b,c);')
    elif variant=='keep_intermediate':body+='    assert b in left;\n'
    elif variant=='lost_value':body+='    assert c in left && left[c] == 0;\n'
    elif variant=='skip_singleton':body='    if |m| > 1 {\n'+body+'    }\n'
    elif variant=='occupied_destination':
        body+='    '+('O1.Certify(mid,b,b);' if depth=='deep' else 'A.ObserveMove(mid,b,b);')+'\n'
    elif variant=='missing_certificate':
        assert depth=='deep';body=body.replace('O1.Certify(mid,b,c);','')
    elif variant!='reference':raise ValueError(variant)
    return body

def helper(name,depth,body,forward=False):
    if forward:
        return 'include "Kernel.dfy"\ninclude "HelperA.dfy"\nmodule HelperB {\n  import K = Kernel`Public\n  import H = HelperA\n'+SIGNATURE+'  {\n    H.Prove(m,a,b,c);\n  }\n}\n'
    view='Public' if depth=='deep' else 'Hidden';api='Deep' if depth=='deep' else 'Shallow'
    return 'include "Kernel.dfy"\ninclude "Ops1.dfy"\ninclude "Ops2.dfy"\ninclude "Api.dfy"\n'+f'module {name} {{\n  import K = Kernel`Public\n  import A = Api`{api}\n  import O1 = Ops1`{view}\n  import O2 = Ops2`{view}\n'+SIGNATURE+'  {\n'+body+'  }\n}\n'

def client(letter):
    head=f'include "Kernel.dfy"\ninclude "Helper{letter}.dfy"\nmodule Client{letter} {{\n  import K = Kernel`Public\n  import H = Helper{letter}\n'
    if letter=='A':return head+SIGNATURE.replace(' {:induction false}','').replace('Prove(','Target(')+'  { H.Prove(m,a,b,c); }\n}\n'
    return head+'''  lemma Target(m: map<int,int>,a: int,b: int,c: int,q: int)
    requires a in m && b !in m && c !in m
    requires a != b && b != c && a != c
    requires q in K.Move(m,a,c)
    ensures q in K.Move(K.Move(m,a,b),b,c)
    ensures K.Move(K.Move(m,a,b),b,c)[q] == K.Move(m,a,c)[q]
  { H.Prove(m,a,b,c); }
}
'''

def sources(depth,sharing,variant):
    body=proof(depth,variant)
    return {'Kernel.dfy':KERNEL,'Ops1.dfy':OPS1,'Ops2.dfy':OPS2,'Api.dfy':API,
        'HelperA.dfy':helper('HelperA',depth,body),'HelperB.dfy':helper('HelperB',depth,body,sharing=='shared'),
        'ClientA.dfy':client('A'),'ClientB.dfy':client('B'),'All.dfy':'include "ClientA.dfy"\ninclude "ClientB.dfy"\n'}

def build():
    tasks=[];checks=[]
    for depth in ('shallow','deep'):
        for sharing in ('shared','separate'):
            tid=f'fresh_move-{depth}-{sharing}';seed=sources(depth,sharing,'empty')
            task=dict(task_id=tid,plan_id='D4-M1',family='finite_map',semantic_instance='fresh_move',depth=depth,sharing=sharing,
                entry='All.dfy',source_sha256=hashes(seed),editable_files=['HelperA.dfy'] if sharing=='shared' else ['HelperA.dfy','HelperB.dfy'],
                development_only=True,held_out=False,minimum_proof_depth=None,model_calls=0)
            tasks.append(task)
            for variant in VARIANTS+(['missing_certificate'] if depth=='deep' else []):
                fs=sources(depth,sharing,variant);rel=f'fixtures/{tid}/{variant}';folder=ROOT/rel;folder.mkdir(parents=True,exist_ok=False)
                for name,text in fs.items():(folder/name).write_text(text)
                expected='success' if variant=='reference' else 'resolution_failure' if variant=='hidden_shortcut' else 'proof_failure'
                checks.append(dict(task_id=tid,variant=variant,path=rel,phase='core' if variant in ('reference','empty') else 'negatives',expected=expected,source_sha256=hashes(fs)))
    for name,data in [('tasks.json',tasks),('checks.json',checks)]:
        with (ROOT/name).open('x') as f:f.write(json.dumps(data,indent=2)+'\n')
    print(json.dumps(dict(semantic_instances=1,workspaces=4,planned_controls=len(checks),model_calls=0,status='CONSTRUCTED_NOT_VERIFIED')))

if __name__=='__main__':build()
