"""Two development instances requiring witness separation and map alias cases.
Pure construction; neither a model client nor a verifier is imported.
"""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def hashes(files):return {n:hashlib.sha256(s.encode()).hexdigest() for n,s in sorted(files.items())}

WK='''module Kernel {
  export Public provides LeftFact, RightFact, Joined, Separated, Room
  export Internal reveals LeftFact, RightFact, Joined, Separated, Room, Witness
  opaque predicate LeftFact(a: int, b: int, w: int) { a <= w <= b }
  opaque predicate RightFact(c: int, d: int, w: int) { c <= w <= d }
  opaque predicate Joined(a: int, b: int, c: int, d: int, w: int) { LeftFact(a,b,w) && RightFact(c,d,w) }
  opaque predicate Separated(u: int, v: int, gap: int) { 0 < gap && u + gap <= v }
  opaque predicate Witness(a: int, b: int, c: int, d: int, gap: int, u: int, v: int) {
    a <= u <= b && c <= u <= d && a <= v <= b && c <= v <= d && 0 < gap && u + gap <= v
  }
  opaque ghost predicate Room(a: int, b: int, c: int, d: int, gap: int) {
    exists u: int, v: int {:trigger Witness(a,b,c,d,gap,u,v)} :: Witness(a,b,c,d,gap,u,v)
  }
}
'''
WO1='''include "Kernel.dfy"
module Ops1 {
  export Hidden provides K
  export Public provides K, Left, Right, Separate
  import K = Kernel`Internal
  lemma Left(a: int, b: int, w: int)
    requires a <= w <= b
    ensures K.LeftFact(a,b,w)
  { reveal K.LeftFact(); }
  lemma Right(c: int, d: int, w: int)
    requires c <= w <= d
    ensures K.RightFact(c,d,w)
  { reveal K.RightFact(); }
  lemma Separate(u: int, v: int, gap: int)
    requires 0 < gap && u + gap <= v
    ensures K.Separated(u,v,gap)
  { reveal K.Separated(); }
}
'''
WO2='''include "Kernel.dfy"
module Ops2 {
  export Hidden provides K
  export Public provides K, Join
  import K = Kernel`Internal
  lemma Join(a: int, b: int, c: int, d: int, w: int)
    requires K.LeftFact(a,b,w) && K.RightFact(c,d,w)
    ensures K.Joined(a,b,c,d,w)
  { reveal K.Joined(); }
}
'''
WA='''include "Kernel.dfy"
module Api {
  export Shallow provides K, Direct
  export Deep provides K, Finish
  import K = Kernel`Internal
  lemma Direct(a: int, b: int, c: int, d: int, gap: int, u: int, v: int)
    requires a <= u <= b && c <= u <= d && a <= v <= b && c <= v <= d
    requires 0 < gap && u + gap <= v
    ensures K.Room(a,b,c,d,gap)
  {
    reveal K.Room(); reveal K.Witness();
    assert K.Witness(a,b,c,d,gap,u,v);
    assert exists p: int, q: int {:trigger K.Witness(a,b,c,d,gap,p,q)} :: K.Witness(a,b,c,d,gap,p,q);
  }
  lemma Finish(a: int, b: int, c: int, d: int, gap: int, u: int, v: int)
    requires K.Joined(a,b,c,d,u) && K.Joined(a,b,c,d,v) && K.Separated(u,v,gap)
    ensures K.Room(a,b,c,d,gap)
  {
    reveal K.Joined(); reveal K.LeftFact(); reveal K.RightFact(); reveal K.Separated();
    Direct(a,b,c,d,gap,u,v);
  }
}
'''
WS='''  lemma {:induction false} Prove(a: int, b: int, c: int, d: int, gap: int)
    requires 0 < gap
    requires a + gap <= b && c + gap <= d && a + gap <= d && c + gap <= b
    ensures K.Room(a,b,c,d,gap)
'''
WVAR=['reference','empty','wrong_lower','short_gap','wrong_upper','missing_membership','missing_second','hidden_shortcut']
MVAR=['reference','empty','skip_alias','skip_distinct','missing_inner','wrong_snapshot','wrong_delete','hidden_shortcut']


def wproof(depth,variant):
    if variant=='empty':return ''
    s='    var u := if a >= c then a else c;\n    var v := u + gap;\n'
    if variant=='hidden_shortcut':return s+('    A.Finish(a,b,c,d,gap,u,v);\n' if depth=='shallow' else '    A.Direct(a,b,c,d,gap,u,v);\n')
    if depth=='shallow':s+='    A.Direct(a,b,c,d,gap,u,v);\n'
    else:s+='''    O1.Left(a,b,u); O1.Right(c,d,u); O2.Join(a,b,c,d,u);
    O1.Left(a,b,v); O1.Right(c,d,v); O2.Join(a,b,c,d,v);
    O1.Separate(u,v,gap); A.Finish(a,b,c,d,gap,u,v);
'''
    if variant=='wrong_lower':s=s.replace('if a >= c then a else c','a')
    elif variant=='short_gap':s=s.replace('u + gap;','u + gap - 1;')
    elif variant=='wrong_upper':s=s.replace('u + gap;','b + 1;')
    elif variant=='missing_membership':s=s.replace('O1.Right(c,d,v);','') if depth=='deep' else s.replace('A.Direct(a,b,c,d,gap,u,v);','A.Direct(a,b,c,d,gap,u,b);')
    elif variant=='missing_second':s=s.replace('O2.Join(a,b,c,d,v);','') if depth=='deep' else s.replace('A.Direct(a,b,c,d,gap,u,v);','A.Direct(a,b,c,d,gap,u,u);')
    elif variant!='reference':raise ValueError(variant)
    return s

MAPBASE=ROOT/'inputs/map-providers'
MS='''  lemma {:induction false} Prove(m: map<int,int>, k: int, j: int, x: int, y: int)
    ensures K.Drop(K.Put(K.Put(m,k,x),j,y),k) == (if k == j then K.Drop(m,k) else K.Put(K.Drop(m,k),j,y))
'''

def mproof(depth,variant):
    if variant=='empty':return ''
    if variant=='hidden_shortcut':return '    O1.PutKeys(m,k,x);\n' if depth=='shallow' else '    A.ObservePut(m,k,x);\n'
    s='''    var u := K.Put(m,k,x);
    var v := K.Put(u,j,y);
    var left := K.Drop(v,k);
    var base := K.Drop(m,k);
    var right := if k == j then base else K.Put(base,j,y);
'''
    if depth=='shallow':
        s+='''    A.ObservePut(m,k,x); A.ObservePut(u,j,y);
    A.ObserveDrop(v,k); A.ObserveDrop(m,k);
    if k != j { A.ObservePut(base,j,y); }
'''
    else:
        s+='''    O1.PutKeys(m,k,x); O1.PutKeys(u,j,y);
    O1.DropKeys(v,k); O1.DropKeys(m,k);
    if k != j { O1.PutKeys(base,j,y); }
'''
    s+='''    assert left.Keys == right.Keys;
    forall q | q in left ensures q in right && left[q] == right[q] {
'''
    if depth=='deep':s+='''      O2.DropAt(v,k,q); O2.PutAt(u,j,y,q);
'''
    if depth=='deep':
        s+='''      if k == j {
        O2.PutAt(m,k,x,q); O2.DropAt(m,k,q);
      } else {
        O2.PutAt(base,j,y,q);
        if q != j { O2.PutAt(m,k,x,q); O2.DropAt(m,k,q); }
      }
'''
    s+='''    }
    A.Equal(left,right);
'''
    if variant=='skip_alias':s='    if k != j {\n'+s+'    }\n'
    elif variant=='skip_distinct':s='    if k == j {\n'+s+'    }\n'
    elif variant=='missing_inner':s=s.replace('O2.PutAt(m,k,x,q);','') if depth=='deep' else s.replace('A.ObservePut(m,k,x);','')
    elif variant=='wrong_snapshot':s=s.replace('O2.PutAt(u,j,y,q);','O2.PutAt(m,j,y,q);') if depth=='deep' else s.replace('A.ObservePut(u,j,y);','A.ObservePut(m,j,y);')
    elif variant=='wrong_delete':s=s.replace('O2.DropAt(v,k,q);','O2.DropAt(v,j,q);') if depth=='deep' else s.replace('A.ObserveDrop(v,k);','A.ObserveDrop(v,j);')
    elif variant!='reference':raise ValueError(variant)
    return s


def helper(name,depth,signature,body,args,forward=False):
    if forward:return ('include "Kernel.dfy"\ninclude "HelperA.dfy"\nmodule HelperB {\n  import K = Kernel`Public\n  import H = HelperA\n'+signature+'  {\n    H.Prove('+args+');\n  }\n}\n')
    view='Public' if depth=='deep' else 'Hidden';api='Deep' if depth=='deep' else 'Shallow'
    return ('include "Kernel.dfy"\ninclude "Ops1.dfy"\ninclude "Ops2.dfy"\ninclude "Api.dfy"\n'+f'module {name} {{\n  import K = Kernel`Public\n  import A = Api`{api}\n  import O1 = Ops1`{view}\n  import O2 = Ops2`{view}\n'+signature+'  {\n'+body+'  }\n}\n')

def client(family,letter):
    header=f'include "Kernel.dfy"\ninclude "Helper{letter}.dfy"\nmodule Client{letter} {{\n  import K = Kernel`Public\n  import H = Helper{letter}\n'
    if family=='separated_witness':
        if letter=='A':return header+WS.replace('Prove','Target').replace(' {:induction false}','')+'  { H.Prove(a,b,c,d,gap); }\n}\n'
        return header+'''  lemma Target(a: int, b: int, c: int, d: int, gap: int, shift: int)
    requires 0 < gap
    requires a + gap <= b && c + gap <= d && a + gap <= d && c + gap <= b
    ensures K.Room(c+shift,d+shift,a+shift,b+shift,gap)
  { H.Prove(c+shift,d+shift,a+shift,b+shift,gap); }
}
'''
    if letter=='A':return header+MS.replace('Prove','Target').replace(' {:induction false}','')+'  { H.Prove(m,k,j,x,y); }\n}\n'
    return header+'''  lemma Target(m: map<int,int>, k: int, j: int, x: int, y: int)
    ensures K.Drop(K.Put(K.Put(m,j,y),k,x),j) == (if j == k then K.Drop(m,j) else K.Put(K.Drop(m,j),k,x))
  { H.Prove(m,j,k,y,x); }
}
'''

def sources(family,depth,sharing,variant):
    if family=='separated_witness':providers={'Kernel.dfy':WK,'Ops1.dfy':WO1,'Ops2.dfy':WO2,'Api.dfy':WA};signature=WS;body=wproof(depth,variant);args='a,b,c,d,gap'
    else:
        providers={n:(MAPBASE/n).read_text() for n in ['Kernel.dfy','Ops1.dfy','Ops2.dfy','Api.dfy']}
        for n in ['Ops1.dfy','Ops2.dfy']:providers[n]=providers[n].replace('  export Public','  export Hidden provides K\n  export Public',1)
        signature=MS;body=mproof(depth,variant);args='m,k,j,x,y'
    return {**providers,'HelperA.dfy':helper('HelperA',depth,signature,body,args),
        'HelperB.dfy':helper('HelperB',depth,signature,body,args,sharing=='shared'),
        'ClientA.dfy':client(family,'A'),'ClientB.dfy':client(family,'B'),
        'All.dfy':'include "ClientA.dfy"\ninclude "ClientB.dfy"\n'}

def build():
    tasks=[];checks=[]
    for family in ['separated_witness','overwrite_delete']:
        for depth in ['shallow','deep']:
            for sharing in ['shared','separate']:
                tid=f'{family}-{depth}-{sharing}';seed=sources(family,depth,sharing,'empty')
                tasks.append(dict(task_id=tid,family='interval_witness' if family=='separated_witness' else 'finite_map',semantic_instance=family,depth=depth,sharing=sharing,entry='All.dfy',source_sha256=hashes(seed),editable_files=['HelperA.dfy'] if sharing=='shared' else ['HelperA.dfy','HelperB.dfy'],development_only=True,model_calls=0))
                for variant in WVAR if family=='separated_witness' else MVAR:
                    files=sources(family,depth,sharing,variant);rel=f'fixtures/{tid}/{variant}';dest=ROOT/rel;dest.mkdir(parents=True,exist_ok=False)
                    for n,s in files.items():(dest/n).write_text(s)
                    checks.append(dict(task_id=tid,variant=variant,path=rel,expected='success' if variant=='reference' else 'resolution_failure' if variant=='hidden_shortcut' else 'proof_failure',source_sha256=hashes(files)))
    for name,data in [('tasks.json',tasks),('checks.json',checks)]:
        with (ROOT/name).open('x') as f:f.write(json.dumps(data,indent=2)+'\n')
    print(json.dumps(dict(tasks=len(tasks),checks=len(checks),source_files=len(checks)*9,model_calls=0)))
if __name__=='__main__':build()
