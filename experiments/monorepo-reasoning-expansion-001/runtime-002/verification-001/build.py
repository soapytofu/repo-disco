"""Six new development obligations. Construction only; no model/SDK/verifier."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def hashes(files):
    return {n: hashlib.sha256(s.encode()).hexdigest() for n, s in sorted(files.items())}


def clamp_family(kind):
    kernel = '''module Kernel {
  export Public provides Lower, Upper, Clamp
  export Internal reveals Lower, Upper, Clamp
  opaque function Lower(x: int, l: int): int { if x < l then l else x }
  opaque function Upper(x: int, h: int): int { if x > h then h else x }
  opaque function Clamp(x: int, l: int, h: int): int
    requires l <= h
  { Upper(Lower(x,l),h) }
}
'''
    ops1 = '''include "Kernel.dfy"
module Ops1 {
  export Public provides K, Lower
  import K = Kernel`Internal
  lemma Lower(x: int, l: int)
    ensures K.Lower(x,l) == (if x < l then l else x)
  { reveal K.Lower(); }
}
'''
    ops2 = '''include "Kernel.dfy"
module Ops2 {
  export Public provides K, Upper
  import K = Kernel`Internal
  lemma Upper(x: int, h: int)
    ensures K.Upper(x,h) == (if x > h then h else x)
  { reveal K.Upper(); }
}
'''
    api = '''include "Kernel.dfy"
module Api {
  export Shallow provides K, Observe
  export Deep provides K, Assemble
  import K = Kernel`Internal
  lemma Observe(x: int, l: int, h: int)
    requires l <= h
    ensures K.Clamp(x,l,h) == (if x < l then l else if x > h then h else x)
  { reveal K.Clamp(); reveal K.Lower(); reveal K.Upper(); }
  lemma Assemble(x: int, l: int, h: int, u: int, v: int)
    requires l <= h && u == K.Lower(x,l) && v == K.Upper(u,h)
    ensures K.Clamp(x,l,h) == v
  { reveal K.Clamp(); }
}
'''
    def observe(depth, x, l, h, i):
        if depth == 'shallow':
            return f'    A.Observe({x},{l},{h});\n'
        return f'''    O1.Lower({x},{l});
    var u{i} := if {x} < {l} then {l} else {x};
    O2.Upper(u{i},{h});
    var v{i} := if u{i} > {h} then {h} else u{i};
    A.Assemble({x},{l},{h},u{i},v{i});
'''
    if kind == 'nested_clamp':
        params = 'x: int, l: int, h: int, a: int, b: int'
        req = '    requires l <= a <= b <= h\n'
        goal = lambda x,l,h,a,b: f'K.Clamp(K.Clamp({x},{l},{h}),{a},{b}) == K.Clamp({x},{a},{b})'
        args = 'x,l,h,a,b'
        target = goal(*args.split(','))
        def proof(depth):
            return observe(depth,'x','l','h',0) + observe(depth,'K.Clamp(x,l,h)','a','b',1) + observe(depth,'x','a','b',2) + '    assert '+target+';\n'
        clients = [(params,req,target,'H.Prove(x,l,h,a,b);'),
                   (params,req,goal('-x','-h','-l','-b','-a'),'H.Prove(-x,-h,-l,-b,-a);')]
        missing = lambda text,depth: text.replace(observe(depth,'K.Clamp(x,l,h)','a','b',1),'')
    else:
        params = 'x: int, delta: int, l: int, h: int'
        req = '    requires delta >= 0 && l <= h\n'
        goal = lambda x,delta,l,h: f'0 <= K.Clamp(({x})+({delta}),{l},{h}) - K.Clamp({x},{l},{h}) <= {delta}'
        args = 'x,delta,l,h'
        target = goal(*args.split(','))
        def proof(depth):
            return observe(depth,'x','l','h',0) + observe(depth,'(x+delta)','l','h',1) + '    assert '+target+';\n'
        clients = [(params,req,target,'H.Prove(x,delta,l,h);'),
                   (params,req,goal('x-delta','delta','l','h'),'H.Prove(x-delta,delta,l,h);')]
        missing = lambda text,depth: text.replace(observe(depth,'(x+delta)','l','h',1),'')
    return dict(id=kind, family='conditional', kernel=kernel,ops1=ops1,ops2=ops2,api=api,
        params=params,requires=req,goal=target,decreases='',args=args,proof=proof,clients=clients,
        mutations={'missing_observation':(missing,'proof_failure'),
                   'wrong_equality':(lambda text,depth:text+'    assert K.Clamp(x,l,h) == x;\n','proof_failure')},
        hidden='A.Observe(x,l,h);', observation_depth=dict(shallow=1,deep=3),
        difficulty='Relate several clamping operations; primitives expose one operation only, never the target composition/stability law.')


def sequence_family(kind):
    if kind == 'reverse_concat':
        kernel = '''module Kernel {
  export Public provides Snoc, Rev
  export Internal reveals Snoc, Rev
  opaque function Snoc(s: seq<int>, x: int): seq<int> { s + [x] }
  opaque function Rev(s: seq<int>): seq<int>
    decreases |s|
  { if |s| == 0 then [] else Snoc(Rev(s[1..]),s[0]) }
}
'''
        ops1 = '''include "Kernel.dfy"
module Ops1 {
  export Public provides K, Unfold
  import K = Kernel`Internal
  lemma Unfold(s: seq<int>)
    requires |s| > 0
    ensures K.Rev(s) == K.Snoc(K.Rev(s[1..]),s[0])
  { reveal K.Rev(); }
}
'''
        ops2 = '''include "Kernel.dfy"
module Ops2 {
  export Public provides K, Snoc
  import K = Kernel`Internal
  lemma Snoc(s: seq<int>, x: int)
    ensures K.Snoc(s,x) == s+[x]
  { reveal K.Snoc(); }
}
'''
        api = '''include "Kernel.dfy"
module Api {
  export Shallow provides K, Empty, Observe
  export Deep provides K, Empty
  import K = Kernel`Internal
  lemma Empty(s: seq<int>)
    requires |s| == 0
    ensures K.Rev(s) == []
  { reveal K.Rev(); }
  lemma Observe(s: seq<int>)
    requires |s| > 0
    ensures K.Rev(s) == K.Rev(s[1..])+[s[0]]
  { reveal K.Rev(); reveal K.Snoc(); }
}
'''
        def observe(depth,s):
            return f'      A.Observe({s});\n' if depth=='shallow' else f'      O1.Unfold({s});\n      O2.Snoc(K.Rev(({s})[1..]),({s})[0]);\n'
        params='s: seq<int>, t: seq<int>';req='';args='s,t';target='K.Rev(s+t) == K.Rev(t)+K.Rev(s)'
        def proof(depth):
            return '''    if |s| == 0 {
      A.Empty(s);
      assert s == [];
    } else {
      Prove(s[1..],t);
'''+observe(depth,'s+t')+observe(depth,'s')+'''      assert (s+t)[1..] == s[1..]+t;
      assert (s+t)[0] == s[0];
    }
    assert K.Rev(s+t) == K.Rev(t)+K.Rev(s);
'''
        clients=[(params,req,target,'H.Prove(s,t);'),
            ('a: seq<int>, b: seq<int>, c: seq<int>','','K.Rev((a+b)+c) == K.Rev(c)+(K.Rev(b)+K.Rev(a))','H.Prove(a+b,c); H.Prove(a,b);')]
        rec='      Prove(s[1..],t);\n';wrong='      Prove(s[1..],[]);\n';nondec='      Prove(s,t);\n';hidden='A.Observe(s);'
    else:
        kernel = '''module Kernel {
  export Public provides Select, Filter
  export Internal reveals Select, Filter
  opaque function Select(x: int, p: int, tail: seq<int>): seq<int>
  { if x <= p then [x]+tail else tail }
  opaque function Filter(s: seq<int>, p: int): seq<int>
    decreases |s|
  { if |s| == 0 then [] else Select(s[0],p,Filter(s[1..],p)) }
}
'''
        ops1 = '''include "Kernel.dfy"
module Ops1 {
  export Public provides K, Unfold
  import K = Kernel`Internal
  lemma Unfold(s: seq<int>, p: int)
    requires |s| > 0
    ensures K.Filter(s,p) == K.Select(s[0],p,K.Filter(s[1..],p))
  { reveal K.Filter(); }
}
'''
        ops2 = '''include "Kernel.dfy"
module Ops2 {
  export Public provides K, Select
  import K = Kernel`Internal
  lemma Select(x: int, p: int, tail: seq<int>)
    ensures K.Select(x,p,tail) == (if x <= p then [x]+tail else tail)
  { reveal K.Select(); }
}
'''
        api = '''include "Kernel.dfy"
module Api {
  export Shallow provides K, Empty, Observe
  export Deep provides K, Empty
  import K = Kernel`Internal
  lemma Empty(s: seq<int>, p: int)
    requires |s| == 0
    ensures K.Filter(s,p) == []
  { reveal K.Filter(); }
  lemma Observe(s: seq<int>, p: int)
    requires |s| > 0
    ensures K.Filter(s,p) == (if s[0] <= p then [s[0]]+K.Filter(s[1..],p) else K.Filter(s[1..],p))
  { reveal K.Filter(); reveal K.Select(); }
}
'''
        def observe(depth,s,p):
            return f'      A.Observe({s},{p});\n' if depth=='shallow' else f'      O1.Unfold({s},{p});\n      O2.Select(({s})[0],{p},K.Filter(({s})[1..],{p}));\n'
        params='s: seq<int>, p: int, q: int';req='    requires q <= p\n';args='s,p,q'
        target='K.Filter(K.Filter(s,p),q) == K.Filter(s,q)'
        def proof(depth):
            return '''    if |s| == 0 {
      A.Empty(s,p); A.Empty(s,q); A.Empty([],q);
    } else {
      Prove(s[1..],p,q);
'''+observe(depth,'s','p')+observe(depth,'s','q')+'''      if s[0] <= p {
'''+observe(depth,'[s[0]]+K.Filter(s[1..],p)','q')+'''      }
    }
    assert K.Filter(K.Filter(s,p),q) == K.Filter(s,q);
'''
        clients=[(params,req,target,'H.Prove(s,p,q);'),
            ('s: seq<int>, p: int, q: int, r: int','    requires r <= q <= p\n','K.Filter(K.Filter(K.Filter(s,p),q),r) == K.Filter(s,r)','H.Prove(s,p,q); H.Prove(s,q,r);')]
        rec='      Prove(s[1..],p,q);\n';wrong='      Prove(s[1..],p,p);\n';nondec='      Prove(s,p,q);\n';hidden='A.Observe(s,p);'
    return dict(id=kind,family='sequence',kernel=kernel,ops1=ops1,ops2=ops2,api=api,
        params=params,requires=req,goal=target,decreases='    decreases |s|\n',args=args,proof=proof,clients=clients,
        mutations={'missing_induction':(lambda text,depth:text.replace(rec,''),'proof_failure'),
                   'wrong_induction_argument':(lambda text,depth:text.replace(rec,wrong),'proof_failure'),
                   'nondecreasing_recursion':(lambda text,depth:text.replace(rec,nondec),'termination_failure')},
        hidden=hidden,observation_depth=dict(shallow=1,deep=2),
        difficulty='Construct the induction and relate transformed sequences; providers expose base/one-step equations, not the client law.')


def map_family(kind):
    kernel = '''module Kernel {
  export Public provides Put, Drop
  export Internal reveals Put, Drop
  opaque function Put(m: map<int,int>, k: int, v: int): map<int,int> { m[k := v] }
  opaque function Drop(m: map<int,int>, k: int): map<int,int>
  { map q | q in m && q != k :: m[q] }
}
'''
    ops1 = '''include "Kernel.dfy"
module Ops1 {
  export Public provides K, PutKeys, DropKeys
  import K = Kernel`Internal
  lemma PutKeys(m: map<int,int>, k: int, v: int)
    ensures K.Put(m,k,v).Keys == m.Keys + {k}
  { reveal K.Put(); }
  lemma DropKeys(m: map<int,int>, k: int)
    ensures K.Drop(m,k).Keys == m.Keys - {k}
  { reveal K.Drop(); }
}
'''
    ops2 = '''include "Kernel.dfy"
module Ops2 {
  export Public provides K, PutAt, DropAt
  import K = Kernel`Internal
  lemma PutAt(m: map<int,int>, k: int, v: int, q: int)
    requires q in K.Put(m,k,v)
    ensures q == k ==> K.Put(m,k,v)[q] == v
    ensures q != k ==> q in m && K.Put(m,k,v)[q] == m[q]
  { reveal K.Put(); }
  lemma DropAt(m: map<int,int>, k: int, q: int)
    requires q in K.Drop(m,k)
    ensures q in m && q != k && K.Drop(m,k)[q] == m[q]
  { reveal K.Drop(); }
}
'''
    api = '''include "Kernel.dfy"
module Api {
  export Shallow provides K, ObservePut, ObserveDrop, Equal
  export Deep provides K, Equal
  import K = Kernel`Internal
  lemma ObservePut(m: map<int,int>, k: int, v: int)
    ensures K.Put(m,k,v) == m[k := v]
  { reveal K.Put(); }
  lemma ObserveDrop(m: map<int,int>, k: int)
    ensures K.Drop(m,k) == (map q | q in m && q != k :: m[q])
  { reveal K.Drop(); }
  lemma Equal(a: map<int,int>, b: map<int,int>)
    requires a.Keys == b.Keys
    requires forall q :: q in a ==> q in b && a[q] == b[q]
    ensures a == b
  { }
}
'''
    def facts(depth,op,args):
        return f'    A.Observe{op}({args});\n' if depth=='shallow' else f'    O1.{op}Keys({args});\n'
    if kind == 'commuting_updates':
        params='m: map<int,int>, k: int, j: int, x: int, y: int';req='    requires k != j\n';args='m,k,j,x,y'
        target='K.Put(K.Put(m,k,x),j,y) == K.Put(K.Put(m,j,y),k,x)'
        def proof(depth):
            head='''    var u := K.Put(m,k,x);
    var v := K.Put(m,j,y);
    var left := K.Put(u,j,y);
    var right := K.Put(v,k,x);
'''+facts(depth,'Put','m,k,x')+facts(depth,'Put','m,j,y')+facts(depth,'Put','u,j,y')+facts(depth,'Put','v,k,x')
            lookup='''      O2.PutAt(u,j,y,q); O2.PutAt(v,k,x,q);
      if q != j { O2.PutAt(m,k,x,q); }
      if q != k { O2.PutAt(m,j,y,q); }
''' if depth=='deep' else ''
            return head+'''    assert left.Keys == right.Keys;
    forall q | q in left
      ensures q in right && left[q] == right[q]
    {
'''+lookup+'''    }
    A.Equal(left,right);
'''
        clients=[(params,req,target,'H.Prove(m,k,j,x,y);'),
            (params,req,'K.Put(K.Put(m,j,y+1),k,x-1) == K.Put(K.Put(m,k,x-1),j,y+1)','H.Prove(m,j,k,y+1,x-1);')]
        missing=lambda text,depth:text.replace(facts(depth,'Put','m,k,x'),'')
        wrong='    assert left == K.Put(m,k,x);\n';hidden='A.ObservePut(m,k,x);'
    else:
        params='m: map<int,int>, k: int, j: int, v: int';req='';args='m,k,j,v'
        def goal(k,j,v):
            return f'K.Drop(K.Put(m,{k},{v}),{j}) == (if {k} == {j} then K.Drop(m,{j}) else K.Put(K.Drop(m,{j}),{k},{v}))'
        target=goal('k','j','v')
        def proof(depth):
            head='''    var inserted := K.Put(m,k,v);
    var removed := K.Drop(m,j);
    var left := K.Drop(inserted,j);
    var right := if k == j then removed else K.Put(removed,k,v);
'''+facts(depth,'Put','m,k,v')+facts(depth,'Drop','inserted,j')+facts(depth,'Drop','m,j')+facts(depth,'Put','removed,k,v')
            lookup='''      O2.DropAt(inserted,j,q);
      O2.PutAt(m,k,v,q);
      if k == j {
        O2.DropAt(m,j,q);
      } else {
        O2.PutAt(removed,k,v,q);
        if q != k { O2.DropAt(m,j,q); }
      }
''' if depth=='deep' else ''
            return head+'''    assert left.Keys == right.Keys;
    forall q | q in left
      ensures q in right && left[q] == right[q]
    {
'''+lookup+'''    }
    A.Equal(left,right);
'''
        clients=[(params,req,target,'H.Prove(m,k,j,v);'),(params,req,goal('j','k','v+1'),'H.Prove(m,j,k,v+1);')]
        missing=lambda text,depth:text.replace(facts(depth,'Drop','m,j'),'')
        wrong='    assert left == K.Put(m,k,v);\n';hidden='A.ObservePut(m,k,v);'
    return dict(id=kind,family='map',kernel=kernel,ops1=ops1,ops2=ops2,api=api,
        params=params,requires=req,goal=target,decreases='',args=args,proof=proof,clients=clients,
        mutations={'missing_domain_or_observation':(missing,'proof_failure'),
                   'wrong_map_identity':(lambda text,depth:text+wrong,'proof_failure')},
        hidden=hidden,observation_depth=dict(shallow=1,deep=2),common_extensionality_stage=1,
        difficulty='Build a universal pointwise argument and equal domains across several updates/deletions, including absent keys and aliasing.')


def families():
    return [clamp_family('nested_clamp'),clamp_family('clamp_stability'),
            sequence_family('reverse_concat'),sequence_family('nested_filter'),
            map_family('commuting_updates'),map_family('delete_after_update')]


def declaration(f, weakened=False):
    return f"  lemma {{:induction false}} Prove({f['params']})\n"+f['requires']+'    ensures '+('true' if weakened else f['goal'])+'\n'+f['decreases']


def snapshot(f, depth, sharing, variant):
    files={'Kernel.dfy':f['kernel'],'Ops1.dfy':f['ops1'],'Ops2.dfy':f['ops2'],'Api.dfy':f['api']}
    for letter in ['A','B']:
        forwarding=sharing=='shared' and letter=='B'
        inc=['Kernel.dfy','HelperA.dfy'] if forwarding else ['Kernel.dfy','Ops1.dfy','Ops2.dfy','Api.dfy']
        imports='  import K = Kernel`Public\n'
        imports += '  import H = HelperA\n' if forwarding else ('  import O1 = Ops1`Public\n  import O2 = Ops2`Public\n' if depth=='deep' else '')+f'  import A = Api`{depth.title()}\n'
        body='    H.Prove('+f['args']+');\n' if forwarding else f['proof'](depth)
        if not forwarding:
            if variant=='empty' or (variant=='only_a' and letter=='B') or (variant=='only_b' and letter=='A'):body=''
            elif variant in f['mutations']:body=f['mutations'][variant][0](body,depth)
            elif variant=='hidden_shortcut':body='    '+f['hidden']+'\n'+body
        name='Helper'+letter
        files[name+'.dfy']=''.join(f'include "{n}"\n' for n in inc)+f'module {name} {{\n'+imports+declaration(f,variant=='weaken_contract' and letter=='A')+'  {\n'+body+'  }\n}\n'
    for letter,(params,req,goal,body) in zip(['A','B'],f['clients']):
        files['Client'+letter+'.dfy']=f'''include "Kernel.dfy"
include "Helper{letter}.dfy"
module Client{letter} {{
  import K = Kernel`Public
  import H = Helper{letter}
  lemma Use({params})
{req}    ensures {goal}
  {{ {body} }}
}}
'''
    files['All.dfy']='include "ClientA.dfy"\ninclude "ClientB.dfy"\n'
    return files


def build(root):
    (root/'fixtures').mkdir(exist_ok=False)
    tasks=[];checks=[]
    for f in families():
        for depth in ['shallow','deep']:
            for sharing in ['shared','separate']:
                task_id=f"{f['id']}-{depth}-{sharing}"
                variants=['reference','empty',*f['mutations'],'weaken_contract']
                if sharing=='separate':variants+=['only_a','only_b']
                if depth=='deep':variants+=['hidden_shortcut']
                for variant in variants:
                    files=snapshot(f,depth,sharing,variant)
                    dest=root/'fixtures'/task_id/variant;dest.mkdir(parents=True)
                    for name,text in files.items():(dest/name).write_text(text)
                    expected='success' if variant=='reference' else 'resolution_failure' if variant=='hidden_shortcut' else f['mutations'].get(variant,(None,'proof_failure'))[1]
                    checks.append(dict(task_id=task_id,variant=variant,path=str(dest.relative_to(root)),expected=expected,source_sha256=hashes(files)))
                tasks.append(dict(task_id=task_id,family=f['family'],semantic_instance=f['id'],split='development',depth=depth,sharing=sharing,
                    entry='All.dfy',editable_files=['HelperA.dfy'] if sharing=='shared' else ['HelperA.dfy','HelperB.dfy'],
                    source_sha256=hashes(snapshot(f,depth,sharing,'empty')),reference_operation_fact_depth=f['observation_depth'][depth],
                    common_extensionality_stage=f.get('common_extensionality_stage',0),depth_not_proven_minimal=True,difficulty_design=f['difficulty'],
                    future_protocol_required=True,no_model_difficulty_claim=True))
    save(root/'tasks.json',tasks);save(root/'checks.json',checks)
    return tasks,checks


if __name__=='__main__':
    tasks,checks=build(ROOT)
    print(len(tasks),'matched variants;',len(checks),'planned checks; no model/verifier calls')
