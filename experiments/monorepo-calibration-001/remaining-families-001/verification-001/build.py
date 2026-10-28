"""Additive calibration fixtures. Pure construction; no transport or verifier."""
import hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def sha(b): return hashlib.sha256(b).hexdigest()
def save(p,x): p.write_text(json.dumps(x,indent=2)+'\n')

def sequence():
 kernel='''module Kernel {
  export Public provides Total, SplitReady, StepReady
  export Internal reveals Total, SplitReady, StepReady
  opaque function Total(s: seq<int>): int
    decreases |s|
  { if |s| == 0 then 0 else s[0] + Total(s[1..]) }
  opaque predicate SplitReady(s: seq<int>, t: seq<int>) {
    |s| > 0 && |s + t| > 0 && (s + t)[0] == s[0] && (s + t)[1..] == s[1..] + t
  }
  opaque predicate StepReady(s: seq<int>, t: seq<int>) {
    SplitReady(s, t) && Total(s[1..] + t) == Total(s[1..]) + Total(t)
  }
}
'''
 stages=[ '''include "Kernel.dfy"
module Stage1 {
  export Public provides K, Split
  import K = Kernel`Internal
  lemma Split(s: seq<int>, t: seq<int>)
    requires |s| > 0
    ensures K.SplitReady(s, t)
  { reveal K.SplitReady(); }
}
''', '''include "Kernel.dfy"
module Stage2 {
  export Public provides K, Lift
  import K = Kernel`Internal
  lemma Lift(s: seq<int>, t: seq<int>)
    requires |s| > 0
    requires K.SplitReady(s, t)
    requires K.Total(s[1..] + t) == K.Total(s[1..]) + K.Total(t)
    ensures K.StepReady(s, t)
  { reveal K.StepReady(); }
}
''', '''include "Kernel.dfy"
module Stage3 {
  export Shallow provides K, Base, Direct
  export Deep provides K, Base, Finish
  import K = Kernel`Internal
  lemma Base(s: seq<int>, t: seq<int>)
    requires |s| == 0
    ensures K.Total(s + t) == K.Total(s) + K.Total(t)
  { reveal K.Total(); assert s == []; assert s + t == t; }
  lemma Direct(s: seq<int>, t: seq<int>)
    requires |s| > 0
    requires K.Total(s[1..] + t) == K.Total(s[1..]) + K.Total(t)
    ensures K.Total(s + t) == K.Total(s) + K.Total(t)
  {
    assert |s + t| > 0;
    assert (s + t)[0] == s[0];
    assert (s + t)[1..] == s[1..] + t;
    reveal K.Total();
    assert K.Total(s + t) == s[0] + K.Total(s[1..] + t);
    assert K.Total(s) == s[0] + K.Total(s[1..]);
  }
  lemma Finish(s: seq<int>, t: seq<int>)
    requires |s| > 0
    requires K.StepReady(s, t)
    ensures K.Total(s + t) == K.Total(s) + K.Total(t)
  {
    reveal K.StepReady(); reveal K.SplitReady(); reveal K.Total();
    assert K.Total(s + t) == s[0] + K.Total(s[1..] + t);
    assert K.Total(s) == s[0] + K.Total(s[1..]);
  }
}
''']
 spec='  lemma {:induction false} Prove(s: seq<int>, t: seq<int>)\n    ensures K.Total(s + t) == K.Total(s) + K.Total(t)\n    decreases |s|\n'
 def proof(d):
  calls='      End.Direct(s, t);\n' if d=='shallow' else '      S1.Split(s, t);\n      S2.Lift(s, t);\n      End.Finish(s, t);\n'
  return '    if |s| == 0 {\n      End.Base(s, t);\n    } else {\n      Prove(s[1..], t);\n'+calls+'    }\n'
 clients=[('s: seq<int>, t: seq<int>', '', 'K.Total(s + t) == K.Total(s) + K.Total(t)', 's, t'),('a: seq<int>, b: seq<int>, c: seq<int>', '', 'K.Total((a + b) + c) == K.Total(a + b) + K.Total(c)', 'a + b, c')]
 return dict(kernel=kernel,stages=stages,spec=spec,proof=proof,clients=clients,args='s, t',family='sequence_induction',instance='opaque-total-append-001',lineage='inspected Total/Append induction; new opaque stage contracts',variables=['s','t'],calls={'End.Base':2,'End.Direct':2,'S1.Split':2,'S2.Lift':2,'End.Finish':2,'Prove':2},reference_depth={'provider_stages_per_induction_step':{'shallow':1,'deep':3},'recursive_edge':'Prove(s[1..],t), not a finite acyclic depth'},mutations={'missing_recursion':lambda b,d:b.replace('      Prove(s[1..], t);\n',''),'nondecreasing_recursion':lambda b,d:b.replace('Prove(s[1..], t)','Prove(s, t)'),'missing_prerequisite':lambda b,d:b.replace('      S2.Lift(s, t);\n','') if d=='deep' else b.replace('      End.Base(s, t);\n',''),'wrong_argument':lambda b,d:b.replace('Prove(s[1..], t)','Prove(s[1..], [])')})

def relational():
 kernel='''module Kernel {
  export Public provides LeftFact, RightFact, Joined, Safe
  export Internal reveals LeftFact, RightFact, Joined, Safe
  opaque predicate LeftFact(x: int, y: int) { 0 <= x <= y }
  opaque predicate RightFact(y: int, z: int) { y <= z }
  opaque predicate Joined(x: int, y: int, z: int) { LeftFact(x, y) && RightFact(y, z) }
  opaque predicate Safe(x: int, z: int) { 0 <= x <= z }
}
'''
 stages=['''include "Kernel.dfy"
module Stage1 {
  export Public provides K, Left, Right
  import K = Kernel`Internal
  lemma Left(x: int, y: int)
    requires 0 <= x <= y
    ensures K.LeftFact(x, y)
  { reveal K.LeftFact(); }
  lemma Right(y: int, z: int)
    requires y <= z
    ensures K.RightFact(y, z)
  { reveal K.RightFact(); }
}
''','''include "Kernel.dfy"
module Stage2 {
  export Public provides K, Join
  import K = Kernel`Internal
  lemma Join(x: int, y: int, z: int)
    requires K.LeftFact(x, y)
    requires K.RightFact(y, z)
    ensures K.Joined(x, y, z)
  { reveal K.Joined(); }
}
''','''include "Kernel.dfy"
module Stage3 {
  export Shallow provides K, Direct
  export Deep provides K, Finish
  import K = Kernel`Internal
  lemma Direct(x: int, y: int, z: int)
    requires 0 <= x <= y <= z
    ensures K.Safe(x, z)
  { reveal K.Safe(); }
  lemma Finish(x: int, y: int, z: int)
    requires K.Joined(x, y, z)
    ensures K.Safe(x, z)
  { reveal K.Joined(); reveal K.LeftFact(); reveal K.RightFact(); reveal K.Safe(); }
}
''']
 spec='  lemma {:induction false} Prove(x: int, y: int, z: int)\n    requires 0 <= x <= y <= z\n    ensures K.Safe(x, z)\n'
 def proof(d):return '    End.Direct(x, y, z);\n' if d=='shallow' else '    S1.Left(x, y);\n    S1.Right(y, z);\n    S2.Join(x, y, z);\n    End.Finish(x, y, z);\n'
 clients=[('x: int, y: int, z: int','    requires 0 <= x <= y <= z\n','K.Safe(x, z)','x, y, z'),('a: int, b: int, c: int','    requires a >= 0 && b >= 0 && c >= a\n','K.Safe(a + b, c + b)','a + b, a + b, c + b')]
 return dict(kernel=kernel,stages=stages,spec=spec,proof=proof,clients=clients,args='x, y, z',family='relational_join',instance='bounded-transitive-diamond-001',lineage='development relation/diamond ancestry; two facts share a join witness',variables=['x','y','z'],calls={'End.Direct':3,'S1.Left':2,'S1.Right':2,'S2.Join':3,'End.Finish':3},reference_depth={'provider_critical_path_stages':{'shallow':1,'deep':3},'call_count':{'shallow':1,'deep':4},'deep_shape':'two Stage1 facts -> Stage2.Join -> Stage3.Finish'},mutations={'missing_prerequisite':lambda b,d:b.replace('    S1.Right(y, z);\n','') if d=='deep' else '', 'wrong_argument':lambda b,d:b.replace('S1.Right(y, z)','S1.Right(x, z)') if d=='deep' else b.replace('End.Direct(x, y, z)','End.Direct(x, z, y)'), 'missing_join':lambda b,d:b.replace('    S2.Join(x, y, z);\n','') if d=='deep' else ''})

def maps():
 kernel='''module Kernel {
  export Public provides Valid, Values, Frame, Ready, FrameTwo
  export Internal reveals Valid, Values, Frame, Ready, FrameTwo
  opaque predicate Valid(m: map<int, int>) { forall q :: q in m ==> m[q] >= 0 }
  opaque predicate Values(m: map<int, int>) { forall q :: q in m ==> m[q] >= 0 }
  opaque predicate Frame(m: map<int, int>, n: map<int, int>, k: int) {
    forall q :: q in m && q != k ==> q in n && n[q] == m[q]
  }
  opaque predicate Ready(m: map<int, int>, k: int, v: int) {
    Values(m[k := v]) && Frame(m, m[k := v], k)
  }
  opaque predicate FrameTwo(m: map<int, int>, n: map<int, int>, k: int, j: int) {
    forall q :: q in m && q != k && q != j ==> q in n && n[q] == m[q]
  }
}
'''
 stages=['''include "Kernel.dfy"
module Stage1 {
  export Public provides K, Update
  import K = Kernel`Internal
  lemma Update(m: map<int, int>, k: int, v: int)
    requires K.Valid(m) && v >= 0
    ensures K.Values(m[k := v])
  { reveal K.Valid(); reveal K.Values(); }
}
''','''include "Kernel.dfy"
module Stage2 {
  export Public provides K, Preserve
  import K = Kernel`Internal
  lemma Preserve(m: map<int, int>, k: int, v: int)
    requires K.Values(m[k := v])
    ensures K.Ready(m, k, v)
  { reveal K.Ready(); reveal K.Frame(); }
}
''','''include "Kernel.dfy"
module Stage3 {
  export Shallow provides K, Direct, Compose
  export Deep provides K, Finish, Compose
  import K = Kernel`Internal
  lemma Direct(m: map<int, int>, k: int, v: int)
    requires K.Valid(m) && v >= 0
    ensures K.Valid(m[k := v]) && K.Frame(m, m[k := v], k)
  { reveal K.Valid(); reveal K.Frame(); }
  lemma Finish(m: map<int, int>, k: int, v: int)
    requires K.Ready(m, k, v)
    ensures K.Valid(m[k := v]) && K.Frame(m, m[k := v], k)
  { reveal K.Ready(); reveal K.Values(); reveal K.Valid(); }
  lemma Compose(m: map<int, int>, k: int, v: int, j: int, w: int)
    requires k != j
    requires K.Frame(m, m[k := v], k)
    requires K.Frame(m[k := v], m[k := v][j := w], j)
    ensures K.FrameTwo(m, m[k := v][j := w], k, j)
    ensures m[k := v][j := w][k] == v && m[k := v][j := w][j] == w
  { reveal K.Frame(); reveal K.FrameTwo(); }
}
''']
 contract='K.Valid(m[k := v][j := w]) && K.FrameTwo(m, m[k := v][j := w], k, j)'
 spec='  lemma {:induction false} Prove(m: map<int, int>, k: int, v: int, j: int, w: int)\n    requires K.Valid(m) && v >= 0 && w >= 0 && k != j\n    ensures '+contract+'\n    ensures m[k := v][j := w][k] == v && m[k := v][j := w][j] == w\n'
 def proof(d):
  calls=[]
  for args in ['m, k, v','m[k := v], j, w']:
   calls += [f'    End.Direct({args});\n'] if d=='shallow' else [f'    S1.Update({args});\n',f'    S2.Preserve({args});\n',f'    End.Finish({args});\n']
  return ''.join(calls)+'    End.Compose(m, k, v, j, w);\n'
 clients=[('m: map<int, int>, k: int, j: int, v: int, w: int','    requires K.Valid(m) && v >= 0 && w >= 0 && k != j\n',contract,'m, k, v, j, w'),('m: map<int, int>, k: int, j: int, v: int, w: int','    requires K.Valid(m) && v >= 0 && w >= 0 && k != j\n','K.Valid(m[j := w][k := v]) && K.FrameTwo(m, m[j := w][k := v], j, k)','m, j, w, k, v')]
 return dict(kernel=kernel,stages=stages,spec=spec,proof=proof,clients=clients,args='m, k, v, j, w',family='finite_map_frames',instance='two-distinct-updates-001',lineage='new development map update/frame composition',variables=['m','k','v','j','w'],calls={'End.Direct':3,'S1.Update':3,'S2.Preserve':3,'End.Finish':3,'End.Compose':5},reference_depth={'provider_stages_per_update':{'shallow':1,'deep':3},'call_count':{'shallow':3,'deep':7},'shape':'two sequential updates then common Compose; Compose shared in both depths'},mutations={'missing_prerequisite':lambda b,d:b.replace('    S2.Preserve(m, k, v);\n','') if d=='deep' else b.replace('    End.Direct(m, k, v);\n',''),'wrong_argument':lambda b,d:b.replace('m[k := v], j, w','m, j, w'),'missing_composition':lambda b,d:b.replace('    End.Compose(m, k, v, j, w);\n','')})

FAMILIES={'sequence':sequence,'relational':relational,'map':maps}
def helper(f,label,depth,body,delegate=False):
 includes='include "Kernel.dfy"\n'
 if delegate:includes+='include "HelperA.dfy"\n';imports='  import H = HelperA\n'
 else:
  includes+=''.join('include "Stage%d.dfy"\n'%i for i in [1,2,3])
  imports=('  import S1 = Stage1`Public\n  import S2 = Stage2`Public\n' if depth=='deep' else '')+f'  import End = Stage3`{"Deep" if depth=="deep" else "Shallow"}\n'
 return includes+f'module Helper{label} {{\n  import K = Kernel`Public\n'+imports+f['spec']+'  {\n'+body+'  }\n}\n'
def snapshot(f,depth,sharing,variant):
 body=f['proof'](depth);a=b=body
 if variant=='empty':a=b=''
 if variant in f['mutations']:a=b=f['mutations'][variant](body,depth)
 if variant=='only_a':b=''
 if variant=='only_b':a=''
 if variant=='hidden_shortcut':a=b=body.replace('End.Finish','End.Direct')
 files={'Kernel.dfy':f['kernel'],**{'Stage%d.dfy'%(i+1):s for i,s in enumerate(f['stages'])}}
 files['HelperA.dfy']=helper(f,'A',depth,a)
 files['HelperB.dfy']=helper(f,'B',depth,'    H.Prove('+f['args']+');\n',True) if sharing=='shared' else helper(f,'B',depth,b)
 for label,(params,req,ens,args) in zip('AB',f['clients']):
  files['Client'+label+'.dfy']=f'include "Kernel.dfy"\ninclude "Helper{label}.dfy"\nmodule Client{label} {{\n  import K = Kernel`Public\n  import H = Helper{label}\n  lemma Use({params})\n'+req+'    ensures '+ens+'\n  { H.Prove('+args+'); }\n}\n'
 files['All.dfy']='include "ClientA.dfy"\ninclude "ClientB.dfy"\n'
 if variant=='weakened_helper_contract':files['HelperA.dfy']=re.sub(r'    ensures [^\n]+','    ensures true',files['HelperA.dfy'])
 return files

def main():
 (ROOT/'fixtures').mkdir(exist_ok=False);tasks=[];checks=[]
 for prefix,maker in FAMILIES.items():
  f=maker()
  for depth in ['shallow','deep']:
   for sharing in ['shared','separate']:
    tid=f'{prefix}-{depth}-{sharing}'
    variants=['reference','empty',*f['mutations'],'weakened_helper_contract']
    if prefix=='relational' and depth=='shallow':variants.remove('missing_join')
    if sharing=='separate':variants+=['only_a','only_b']
    if depth=='deep':variants+=['hidden_shortcut']
    for variant in variants:
     files=snapshot(f,depth,sharing,variant);path=ROOT/'fixtures'/tid/variant;path.mkdir(parents=True)
     for n,t in files.items():(path/n).write_text(t)
     checks.append(dict(task_id=tid,variant=variant,path=str(path.relative_to(ROOT)),expected='success' if variant=='reference' else 'resolution_failure' if variant=='hidden_shortcut' else 'proof_failure',source_sha256={n:sha(t.encode()) for n,t in files.items()}))
    files=snapshot(f,depth,sharing,'empty')
    tasks.append(dict(task_id=tid,family=f['family'],semantic_instance=f['instance'],lineage=f['lineage'],split='calibration-development',repository_boundary='single_monorepo_workspace',depth=depth,sharing=sharing,entry='All.dfy',editable_files=['HelperA.dfy'] if sharing=='shared' else ['HelperA.dfy','HelperB.dfy'],client_count=2,reference_depth=f['reference_depth'],reference_depth_not_minimal=True,variables=f['variables'],calls={n:a for n,a in f['calls'].items() if (n.startswith('S') or n=='End.Finish') and depth=='deep' or n=='End.Direct' and depth=='shallow' or n in ['End.Base','End.Compose','Prove']},source_sha256={n:sha(t.encode()) for n,t in files.items()},bytes=sum(len(t.encode()) for t in files.values()),includes={n:re.findall(r'include "([^"]+)"',t) for n,t in files.items()}))
 save(ROOT/'tasks.json',tasks);save(ROOT/'checks.json',checks)
 print(len(tasks),'variants;',len(checks),'verifier controls; zero model calls')
if __name__=='__main__':main()
