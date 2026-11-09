"""Four proposed development tasks, deterministic construction without models/Dafny."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def hashes(fs):return {n:hashlib.sha256(s.encode()).hexdigest() for n,s in sorted(fs.items())}

AK='''module Kernel {
  export Public provides UBound, VBound, Bounds, Balanced, Feasible
  export Internal reveals UBound, VBound, Bounds, Balanced, Witness, Feasible
  opaque predicate UBound(a: int,b: int,u: int) { a <= u <= b }
  opaque predicate VBound(c: int,d: int,v: int) { c <= v <= d }
  opaque predicate Bounds(a: int,b: int,c: int,d: int,u: int,v: int) { UBound(a,b,u) && VBound(c,d,v) }
  opaque predicate Balanced(t: int,u: int,v: int) { u+v == t }
  opaque predicate Witness(a: int,b: int,c: int,d: int,t: int,u: int,v: int) { a<=u<=b && c<=v<=d && u+v==t }
  opaque ghost predicate Feasible(a: int,b: int,c: int,d: int,t: int) {
    exists u: int,v: int {:trigger Witness(a,b,c,d,t,u,v)} :: Witness(a,b,c,d,t,u,v)
  }
}
'''
AO1='''include "Kernel.dfy"
module Ops1 {
  export Hidden provides K
  export Public provides K, Left, Right, Balance
  import K = Kernel`Internal
  lemma Left(a: int,b: int,u: int)
    requires a<=u<=b
    ensures K.UBound(a,b,u)
  { reveal K.UBound(); }
  lemma Right(c: int,d: int,v: int)
    requires c<=v<=d
    ensures K.VBound(c,d,v)
  { reveal K.VBound(); }
  lemma Balance(t: int,u: int,v: int)
    requires u+v==t
    ensures K.Balanced(t,u,v)
  { reveal K.Balanced(); }
}
'''
AO2='''include "Kernel.dfy"
module Ops2 {
  export Hidden provides K
  export Public provides K, Join
  import K = Kernel`Internal
  lemma Join(a: int,b: int,c: int,d: int,u: int,v: int)
    requires K.UBound(a,b,u) && K.VBound(c,d,v)
    ensures K.Bounds(a,b,c,d,u,v)
  { reveal K.Bounds(); }
}
'''
AA='''include "Kernel.dfy"
module Api {
  export Shallow provides K, Direct
  export Deep provides K, Finish
  import K = Kernel`Internal
  lemma Direct(a: int,b: int,c: int,d: int,t: int,u: int,v: int)
    requires a<=u<=b && c<=v<=d && u+v==t
    ensures K.Feasible(a,b,c,d,t)
  {
    reveal K.Feasible(); reveal K.Witness();
    assert K.Witness(a,b,c,d,t,u,v);
    assert exists p: int,q: int {:trigger K.Witness(a,b,c,d,t,p,q)} :: K.Witness(a,b,c,d,t,p,q);
  }
  lemma Finish(a: int,b: int,c: int,d: int,t: int,u: int,v: int)
    requires K.Bounds(a,b,c,d,u,v) && K.Balanced(t,u,v)
    ensures K.Feasible(a,b,c,d,t)
  {
    reveal K.Bounds(); reveal K.UBound(); reveal K.VBound(); reveal K.Balanced();
    Direct(a,b,c,d,t,u,v);
  }
}
'''
AS='''  lemma {:induction false} Prove(a: int,b: int,c: int,d: int,t: int)
    requires a<=b && c<=d && a+c<=t<=b+d
    ensures K.Feasible(a,b,c,d,t)
'''

def allocation(depth,v):
 if v=='empty':return ''
 body='    var u := if a >= t-d then a else t-d;\n    var w := t-u;\n'
 if v=='hidden_shortcut':return body+('    A.Finish(a,b,c,d,t,u,w);\n' if depth=='shallow' else '    A.Direct(a,b,c,d,t,u,w);\n')
 body+=('    A.Direct(a,b,c,d,t,u,w);\n' if depth=='shallow' else '''    O1.Left(a,b,u); O1.Right(c,d,w);
    O2.Join(a,b,c,d,u,w); O1.Balance(t,u,w);
    A.Finish(a,b,c,d,t,u,w);
''')
 if v=='wrong_endpoint':body=body.replace('if a >= t-d then a else t-d','a')
 elif v=='wrong_total':body=body.replace('var w := t-u;','var w := t-u+1;')
 elif v=='wrong_limit':body=body.replace('if a >= t-d then a else t-d','b+1')
 elif v=='missing_prerequisite':body=body.replace('O1.Right(c,d,w);','') if depth=='deep' else '    if t > a+c {\n'+body+'    }\n'
 elif v!='reference':raise ValueError(v)
 return body

MK='''module Kernel {
  export Public provides Swap
  export Internal reveals Swap
  opaque function Swap(m: map<int,int>,k: int,j: int): map<int,int> {
    if k in m && j in m then m[k := m[j]][j := m[k]] else m
  }
}
'''
MO1='''include "Kernel.dfy"
module Ops1 {
  export Hidden provides K
  export Public provides K, SwapKeys
  import K = Kernel`Internal
  lemma SwapKeys(m: map<int,int>,k: int,j: int)
    requires k in m && j in m
    ensures K.Swap(m,k,j).Keys == m.Keys
  { reveal K.Swap(); }
}
'''
MO2='''include "Kernel.dfy"
module Ops2 {
  export Hidden provides K
  export Public provides K, SwapAt
  import K = Kernel`Internal
  lemma SwapAt(m: map<int,int>,k: int,j: int,q: int)
    requires k in m && j in m && q in m
    ensures q in K.Swap(m,k,j)
    ensures K.Swap(m,k,j)[q] == (if q==k then m[j] else if q==j then m[k] else m[q])
  { reveal K.Swap(); if k==j { assert m[k]==m[j]; } }
}
'''
MA='''include "Kernel.dfy"
module Api {
  export Shallow provides K, ObserveSwap, Equal
  export Deep provides K, Equal
  import K = Kernel`Internal
  lemma ObserveSwap(m: map<int,int>,k: int,j: int)
    requires k in m && j in m
    ensures K.Swap(m,k,j).Keys == m.Keys
    ensures forall q :: q in m ==> q in K.Swap(m,k,j) && K.Swap(m,k,j)[q] == (if q==k then m[j] else if q==j then m[k] else m[q])
  { reveal K.Swap(); if k==j { assert m[k]==m[j]; } }
  lemma Equal(a: map<int,int>,b: map<int,int>)
    requires a.Keys==b.Keys
    requires forall q :: q in a ==> q in b && a[q]==b[q]
    ensures a==b
  { }
}
'''
MS='''  lemma {:induction false} Prove(m: map<int,int>,k: int,j: int)
    requires k in m && j in m
    ensures K.Swap(K.Swap(m,k,j),k,j)==m
'''

def swap(depth,v):
 if v=='empty':return ''
 if v=='hidden_shortcut':return '    O1.SwapKeys(m,k,j);\n' if depth=='shallow' else '    A.ObserveSwap(m,k,j);\n'
 body='''    var once := K.Swap(m,k,j);
    var twice := K.Swap(once,k,j);
'''
 body+=('    A.ObserveSwap(m,k,j); A.ObserveSwap(once,k,j);\n' if depth=='shallow' else '    O1.SwapKeys(m,k,j); O1.SwapKeys(once,k,j);\n')
 body+='''    assert m.Keys == twice.Keys;
    forall q | q in m ensures q in twice && m[q]==twice[q] {
'''
 if depth=='deep':body+='''      O2.SwapAt(once,k,j,q);
      O2.SwapAt(m,k,j,k); O2.SwapAt(m,k,j,j); O2.SwapAt(m,k,j,q);
'''
 body+='''    }
    A.Equal(m,twice);
'''
 if v=='wrong_snapshot':body=body.replace('O2.SwapAt(once,k,j,q);','O2.SwapAt(m,k,j,q);') if depth=='deep' else body.replace('A.ObserveSwap(once,k,j);','A.ObserveSwap(m,k,j);')
 elif v=='missing_inner':
  body=body.replace('O2.SwapAt(m,k,j,k); O2.SwapAt(m,k,j,j); O2.SwapAt(m,k,j,q);','') if depth=='deep' else body.replace('A.ObserveSwap(m,k,j);','O1.SwapKeys(m,k,j);')
  # A shallow control cannot call a hidden observation; keep domain knowledge via a plain premise already available after observing the outer map only.
  if depth=='shallow':body=body.replace('O1.SwapKeys(m,k,j);','')
 elif v=='skip_alias':body='    if k!=j {\n'+body+'    }\n'
 elif v=='skip_distinct':body='    if k==j {\n'+body+'    }\n'
 elif v=='wrong_value':body+='    assert once[k]==m[k];\n'
 elif v!='reference':raise ValueError(v)
 return body

CK='''module Kernel {
  export Public provides Clamp, Region reveals Abs
  export Internal reveals Clamp, Region, Abs
  function Abs(x: int): int { if x<0 then -x else x }
  opaque function Clamp(l: int,h: int,x: int): int { if x<l then l else if x>h then h else x }
  opaque predicate Region(l: int,h: int,x: int,r: int) {
    l<=h && ((r==0 && x<l) || (r==1 && l<=x<=h) || (r==2 && x>h))
  }
}
'''
CO1='''include "Kernel.dfy"
module Ops1 {
  export Hidden provides K
  export Public provides K, Below, Within, Above
  import K = Kernel`Internal
  lemma Below(l: int,h: int,x: int)
    requires l<=h && x<l
    ensures K.Region(l,h,x,0)
  { reveal K.Region(); }
  lemma Within(l: int,h: int,x: int)
    requires l<=x<=h
    ensures K.Region(l,h,x,1)
  { reveal K.Region(); }
  lemma Above(l: int,h: int,x: int)
    requires l<=h && x>h
    ensures K.Region(l,h,x,2)
  { reveal K.Region(); }
}
'''
CO2='''include "Kernel.dfy"
module Ops2 {
  export Hidden provides K
  export Public provides K, ReadBelow, ReadWithin, ReadAbove
  import K = Kernel`Internal
  lemma ReadBelow(l: int,h: int,x: int)
    requires K.Region(l,h,x,0)
    ensures K.Clamp(l,h,x)==l
  { reveal K.Region(); reveal K.Clamp(); }
  lemma ReadWithin(l: int,h: int,x: int)
    requires K.Region(l,h,x,1)
    ensures K.Clamp(l,h,x)==x
  { reveal K.Region(); reveal K.Clamp(); }
  lemma ReadAbove(l: int,h: int,x: int)
    requires K.Region(l,h,x,2)
    ensures K.Clamp(l,h,x)==h
  { reveal K.Region(); reveal K.Clamp(); }
}
'''
CA='''include "Kernel.dfy"
module Api {
  export Shallow provides K, Below, Within, Above
  export Deep provides K
  import K = Kernel`Internal
  lemma Below(l: int,h: int,x: int)
    requires l<=h && x<l
    ensures K.Clamp(l,h,x)==l
  { reveal K.Clamp(); }
  lemma Within(l: int,h: int,x: int)
    requires l<=x<=h
    ensures K.Clamp(l,h,x)==x
  { reveal K.Clamp(); }
  lemma Above(l: int,h: int,x: int)
    requires l<=h && x>h
    ensures K.Clamp(l,h,x)==h
  { reveal K.Clamp(); }
}
'''
CS='''  lemma {:induction false} Prove(l: int,h: int,x: int,y: int)
    requires l<=h
    ensures K.Abs(K.Clamp(l,h,x)-K.Clamp(l,h,y)) <= K.Abs(x-y)
'''

def observe_clamp(depth,x):
 def calls(c):return f'A.{c}(l,h,{x});' if depth=='shallow' else f'O1.{c}(l,h,{x}); O2.Read{c}(l,h,{x});'
 return f'''    if {x}<l {{ {calls('Below')} }}
    else if {x}<=h {{ {calls('Within')} }}
    else {{ {calls('Above')} }}
'''
def clamp(depth,v):
 if v=='empty':return ''
 if v=='hidden_shortcut':return '    O1.Below(l,h,x);\n' if depth=='shallow' else '    A.Below(l,h,x);\n'
 body=observe_clamp(depth,'x')+observe_clamp(depth,'y')+'''    if x<=y {
      assert K.Clamp(l,h,x)<=K.Clamp(l,h,y);
      assert K.Clamp(l,h,y)-K.Clamp(l,h,x)<=y-x;
    } else {
      assert K.Clamp(l,h,y)<=K.Clamp(l,h,x);
      assert K.Clamp(l,h,x)-K.Clamp(l,h,y)<=x-y;
    }
'''
 if v=='missing_x':body=body.replace(observe_clamp(depth,'x'),'')
 elif v=='wrong_boundary':body=body.replace('if x<l {','if x<=l {')
 elif v=='wrong_argument':body=body.replace('A.Within(l,h,x);','A.Within(l,h,y);') if depth=='shallow' else body.replace('O1.Within(l,h,x);','O1.Within(l,h,y);')
 elif v=='skip_cross':body='    if !(x<l && y>h) {\n'+body+'    }\n'
 elif v=='isometry':body+='    assert K.Abs(K.Clamp(l,h,x)-K.Clamp(l,h,y)) == K.Abs(x-y);\n'
 elif v!='reference':raise ValueError(v)
 return body

PK='''module Kernel {
  export Public provides Prefix, StepFact
  export Internal reveals Total, Prefix, StepFact
  opaque function Total(s: seq<int>): int
    decreases |s|
  { if |s|==0 then 0 else s[0]+Total(s[1..]) }
  opaque function Prefix(s: seq<int>,n: int): int
    requires 0<=n<=|s|
  { Total(s[..n]) }
  opaque predicate StepFact(s: seq<int>,n: int)
    requires 0<=n<=|s|
  { if n==0 then Prefix(s,n)==0 else Prefix(s,n)==s[0]+Prefix(s[1..],n-1) }
}
'''
PO1='''include "Kernel.dfy"
module Ops1 {
  export Hidden provides K
  export Public provides K, Unfold
  import K = Kernel`Internal
  lemma Unfold(s: seq<int>,n: int)
    requires 0<=n<=|s|
    ensures K.StepFact(s,n)
  {
    reveal K.StepFact(); reveal K.Prefix(); reveal K.Total();
    if n==0 { assert s[..0]==[]; }
    else {
      assert |s[..n]|>0;
      assert (s[..n])[0]==s[0];
      assert (s[..n])[1..] == (s[1..])[..n-1];
    }
  }
}
'''
PO2='''include "Kernel.dfy"
module Ops2 {
  export Hidden provides K
  export Public provides K, Expose
  import K = Kernel`Internal
  lemma Expose(s: seq<int>,n: int)
    requires 0<=n<=|s|
    requires K.StepFact(s,n)
    ensures if n==0 then K.Prefix(s,n)==0 else K.Prefix(s,n)==s[0]+K.Prefix(s[1..],n-1)
  { reveal K.StepFact(); }
}
'''
PA='''include "Kernel.dfy"
include "Ops1.dfy"
include "Ops2.dfy"
module Api {
  export Shallow provides K, Observe
  export Deep provides K
  import K = Kernel`Public
  import O1 = Ops1`Public
  import O2 = Ops2`Public
  lemma Observe(s: seq<int>,n: int)
    requires 0<=n<=|s|
    ensures if n==0 then K.Prefix(s,n)==0 else K.Prefix(s,n)==s[0]+K.Prefix(s[1..],n-1)
  { O1.Unfold(s,n); O2.Expose(s,n); }
}
'''
PS='''  lemma {:induction false} Prove(s: seq<int>,i: int,j: int)
    requires 0<=i<=|s| && 0<=j<=|s|-i
    ensures K.Prefix(s,i+j)==K.Prefix(s,i)+K.Prefix(s[i..],j)
    decreases i
'''

def prefix(depth,v):
 if v=='empty':return ''
 if v=='hidden_shortcut':return '    O1.Unfold(s,i);\n' if depth=='shallow' else '    A.Observe(s,i);\n'
 def obs(n):return f'A.Observe(s,{n});' if depth=='shallow' else f'O1.Unfold(s,{n}); O2.Expose(s,{n});'
 body=f'''    if i==0 {{
      {obs('0')}
      assert s[0..]==s;
    }} else {{
      {obs('i+j')}
      {obs('i')}
      Prove(s[1..],i-1,j);
      assert (s[1..])[i-1..]==s[i..];
    }}
'''
 if v=='no_base':body=body.replace(obs('0'),'')
 elif v=='no_step':body=body.replace(obs('i+j'),'')
 elif v=='wrong_split':body=body.replace('Prove(s[1..],i-1,j);','if j>0 { Prove(s[1..],i-1,j-1); }')
 elif v=='wrong_argument':body=body.replace('Prove(s[1..],i-1,j);','Prove(s[1..],i-1,j+1);')
 elif v=='nondecreasing':body=body.replace('Prove(s[1..],i-1,j);','Prove(s,i,j);')
 elif v!='reference':raise ValueError(v)
 return body

DEFS={
 'bounded_allocation':dict(plan_id='D3-C1',family='constraint_witness',providers=[AK,AO1,AO2,AA],signature=AS,args='a,b,c,d,t',proof=allocation,variants=['reference','empty','wrong_endpoint','wrong_total','wrong_limit','missing_prerequisite','hidden_shortcut']),
 'map_swap':dict(plan_id='D4-C1',family='finite_map',providers=[MK,MO1,MO2,MA],signature=MS,args='m,k,j',proof=swap,variants=['reference','empty','wrong_snapshot','missing_inner','skip_alias','skip_distinct','wrong_value','hidden_shortcut']),
 'clamp_distance':dict(plan_id='D1-C1',family='conditional',providers=[CK,CO1,CO2,CA],signature=CS,args='l,h,x,y',proof=clamp,variants=['reference','empty','missing_x','wrong_boundary','wrong_argument','skip_cross','isometry','hidden_shortcut']),
 'prefix_split':dict(plan_id='D2-C1',family='sequence',providers=[PK,PO1,PO2,PA],signature=PS,args='s,i,j',proof=prefix,variants=['reference','empty','no_base','no_step','wrong_split','wrong_argument','nondecreasing','hidden_shortcut'])}

def helper(name,depth,sig,body,args,forward=False):
 body='\n'.join(line.rstrip() for line in body.splitlines())+('\n' if body else '')
 if forward:return 'include "Kernel.dfy"\ninclude "HelperA.dfy"\nmodule HelperB {\n  import K = Kernel`Public\n  import H = HelperA\n'+sig+'  {\n    H.Prove('+args+');\n  }\n}\n'
 view='Public' if depth=='deep' else 'Hidden';api='Deep' if depth=='deep' else 'Shallow'
 return 'include "Kernel.dfy"\ninclude "Ops1.dfy"\ninclude "Ops2.dfy"\ninclude "Api.dfy"\n'+f'module {name} {{\n  import K = Kernel`Public\n  import A = Api`{api}\n  import O1 = Ops1`{view}\n  import O2 = Ops2`{view}\n'+sig+'  {\n'+body+'  }\n}\n'

def client(instance,letter):
 d=DEFS[instance];head=f'include "Kernel.dfy"\ninclude "Helper{letter}.dfy"\nmodule Client{letter} {{\n  import K = Kernel`Public\n  import H = Helper{letter}\n'
 if letter=='A':return head+d['signature'].replace(' {:induction false}','').replace('Prove(','Target(')+'  { H.Prove('+d['args']+'); }\n}\n'
 if instance=='bounded_allocation':body='''  lemma Target(a: int,b: int,c: int,d: int,t: int,shift: int)
    requires a<=b && c<=d && a+c<=t<=b+d
    ensures K.Feasible(c+shift,d+shift,a+shift,b+shift,t+2*shift)
  { H.Prove(c+shift,d+shift,a+shift,b+shift,t+2*shift); }
'''
 elif instance=='map_swap':body='''  lemma Target(m: map<int,int>,k: int,j: int,q: int)
    requires k in m && j in m && q in m
    ensures q in K.Swap(K.Swap(m,j,k),j,k) && K.Swap(K.Swap(m,j,k),j,k)[q]==m[q]
  { H.Prove(m,j,k); }
'''
 elif instance=='clamp_distance':body='''  lemma Target(l: int,h: int,x: int,y: int,eps: int)
    requires l<=h && K.Abs(x-y)<=eps
    ensures K.Abs(K.Clamp(l,h,x)-K.Clamp(l,h,y))<=eps
  { H.Prove(l,h,x,y); }
'''
 else:body='''  lemma Target(s: seq<int>,k: int)
    requires 0<=k<=|s|
    ensures K.Prefix(s,|s|)==K.Prefix(s,k)+K.Prefix(s[k..],|s|-k)
  { H.Prove(s,k,|s|-k); }
'''
 return head+body+'}\n'

def sources(instance,depth,sharing,variant):
 d=DEFS[instance];p=dict(zip(['Kernel.dfy','Ops1.dfy','Ops2.dfy','Api.dfy'],d['providers']))
 body=d['proof'](depth,variant)
 return {**p,'HelperA.dfy':helper('HelperA',depth,d['signature'],body,d['args']),
 'HelperB.dfy':helper('HelperB',depth,d['signature'],body,d['args'],sharing=='shared'),
 'ClientA.dfy':client(instance,'A'),'ClientB.dfy':client(instance,'B'),'All.dfy':'include "ClientA.dfy"\ninclude "ClientB.dfy"\n'}

def build():
 tasks=[];checks=[]
 for instance,d in DEFS.items():
  for depth in ['shallow','deep']:
   for sharing in ['shared','separate']:
    tid=f'{instance}-{depth}-{sharing}';seed=sources(instance,depth,sharing,'empty')
    tasks.append(dict(task_id=tid,plan_id=d['plan_id'],family=d['family'],semantic_instance=instance,depth=depth,sharing=sharing,entry='All.dfy',source_sha256=hashes(seed),editable_files=['HelperA.dfy'] if sharing=='shared' else ['HelperA.dfy','HelperB.dfy'],development_only=True,held_out=False,minimum_proof_depth=None,model_calls=0))
    for v in d['variants']:
     fs=sources(instance,depth,sharing,v);rel=f'fixtures/{tid}/{v}';dest=ROOT/rel;dest.mkdir(parents=True,exist_ok=False)
     for n,s in fs.items():(dest/n).write_text(s)
     expected='success' if v=='reference' else 'resolution_failure' if v=='hidden_shortcut' else 'termination_failure' if v=='nondecreasing' else 'proof_failure'
     checks.append(dict(task_id=tid,variant=v,path=rel,phase='core' if v in ['reference','empty'] else 'negatives',expected=expected,source_sha256=hashes(fs)))
 for name,data in [('tasks.json',tasks),('checks.json',checks)]:
  with (ROOT/name).open('x') as f:f.write(json.dumps(data,indent=2)+'\n')
 print(json.dumps(dict(instances=len(DEFS),tasks=len(tasks),checks=len(checks),source_files=len(checks)*9,model_calls=0)))
if __name__=='__main__':build()
