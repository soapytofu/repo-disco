"""Two new development obligations; no verifier/model execution."""
import hashlib,importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OLD=ROOT.parents[1]/'monorepo-calibration-001/remaining-families-001/build.py'
spec=importlib.util.spec_from_file_location('old_builder',OLD)
builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
def sha(s):return hashlib.sha256(s.encode()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n')

def sequence():
 kernel='''module Kernel {
  export Public provides Score, SplitReady, StepReady
  export Internal reveals Score, SplitReady, StepReady
  opaque function Score(s: seq<int>, o: int): int
    decreases |s|
  { if |s| == 0 then 0 else o * s[0] + Score(s[1..], o + 1) }
  opaque predicate SplitReady(s: seq<int>, t: seq<int>, o: int) {
    |s| > 0 && |s + t| > 0 && (s+t)[0] == s[0] &&
    (s+t)[1..] == s[1..] + t && o + 1 + |s[1..]| == o + |s|
  }
  opaque predicate StepReady(s: seq<int>, t: seq<int>, o: int) {
    |s| > 0 && SplitReady(s,t,o) &&
    Score(s[1..]+t,o+1) == Score(s[1..],o+1) + Score(t,(o+1)+|s[1..]|)
  }
}
'''
 stages=['''include "Kernel.dfy"
module Stage1 {
  export Public provides K, Split
  import K = Kernel`Internal
  lemma Split(s: seq<int>, t: seq<int>, o: int)
    requires |s| > 0
    ensures K.SplitReady(s,t,o)
  { reveal K.SplitReady(); }
}
''','''include "Kernel.dfy"
module Stage2 {
  export Public provides K, Lift
  import K = Kernel`Internal
  lemma Lift(s: seq<int>, t: seq<int>, o: int)
    requires |s| > 0 && K.SplitReady(s,t,o)
    requires K.Score(s[1..]+t,o+1) == K.Score(s[1..],o+1) + K.Score(t,(o+1)+|s[1..]|)
    ensures K.StepReady(s,t,o)
  { reveal K.StepReady(); }
}
''','''include "Kernel.dfy"
module Stage3 {
  export Shallow provides K, Base, Direct
  export Deep provides K, Base, Finish
  import K = Kernel`Internal
  lemma Base(s: seq<int>, t: seq<int>, o: int)
    requires |s| == 0
    ensures K.Score(s+t,o) == K.Score(s,o) + K.Score(t,o+|s|)
  { reveal K.Score(); assert s == []; assert s+t == t; }
  lemma Direct(s: seq<int>, t: seq<int>, o: int)
    requires |s| > 0
    requires K.Score(s[1..]+t,o+1) == K.Score(s[1..],o+1) + K.Score(t,(o+1)+|s[1..]|)
    ensures K.Score(s+t,o) == K.Score(s,o) + K.Score(t,o+|s|)
  {
    assert |s+t| > 0;
    assert (s+t)[0] == s[0];
    assert (s+t)[1..] == s[1..]+t;
    assert (o+1)+|s[1..]| == o+|s|;
    reveal K.Score();
    assert K.Score(s+t,o) == o*s[0] + K.Score(s[1..]+t,o+1);
    assert K.Score(s,o) == o*s[0] + K.Score(s[1..],o+1);
  }
  lemma Finish(s: seq<int>, t: seq<int>, o: int)
    requires |s| > 0 && K.StepReady(s,t,o)
    ensures K.Score(s+t,o) == K.Score(s,o) + K.Score(t,o+|s|)
  {
    reveal K.StepReady(); reveal K.SplitReady(); reveal K.Score();
    assert K.Score(s+t,o) == o*s[0] + K.Score(s[1..]+t,o+1);
    assert K.Score(s,o) == o*s[0] + K.Score(s[1..],o+1);
  }
}
''']
 spec='  lemma {:induction false} Prove(s: seq<int>, t: seq<int>, o: int)\n    ensures K.Score(s+t,o) == K.Score(s,o) + K.Score(t,o+|s|)\n    decreases |s|\n'
 def proof(d):
  chain='      End.Direct(s,t,o);\n' if d=='shallow' else '      S1.Split(s,t,o);\n      S2.Lift(s,t,o);\n      End.Finish(s,t,o);\n'
  return '    if |s| == 0 {\n      End.Base(s,t,o);\n    } else {\n      Prove(s[1..],t,o+1);\n'+chain+'    }\n'
 clients=[('s: seq<int>, t: seq<int>, o: int','','K.Score(s+t,o) == K.Score(s,o) + K.Score(t,o+|s|)','s,t,o'),('a: seq<int>, b: seq<int>, c: seq<int>, o: int','','K.Score((a+b)+c,o) == K.Score(a+b,o) + K.Score(c,o+|a+b|)','a+b,c,o')]
 return dict(kernel=kernel,stages=stages,spec=spec,proof=proof,clients=clients,args='s,t,o',family='sequence_offset',instance='offset-weighted-concatenation-001',lineage='development append induction ancestry; weighted Score requires generalized offset o+1 in recursive hypothesis and shifted suffix o+length(s)',variables=['s','t','o'],calls={'End.Base':3,'End.Direct':3,'S1.Split':3,'S2.Lift':3,'End.Finish':3,'Prove':3},mutations={
  'missing_recursion':lambda b,d:b.replace('      Prove(s[1..],t,o+1);\n',''),
  'fixed_offset':lambda b,d:b.replace('Prove(s[1..],t,o+1)','Prove(s[1..],t,o)'),
  'missing_base':lambda b,d:b.replace('      End.Base(s,t,o);\n',''),
  'wrong_tail':lambda b,d:b.replace('Prove(s[1..],t,o+1)','Prove(s[1..],[],o+1)'),
  'nondecreasing_recursion':lambda b,d:b.replace('Prove(s[1..],t,o+1)','Prove(s,t,o+1)'),
  'missing_step':lambda b,d:b.replace('      S2.Lift(s,t,o);\n','') if d=='deep' else b.replace('      End.Direct(s,t,o);\n','')})

def relational():
 kernel='''module Kernel {
  export Public provides LeftFact, RightFact, Joined, Overlap
  export Internal reveals LeftFact, RightFact, Joined, Overlap
  opaque predicate LeftFact(a: int, b: int, w: int) { a <= w <= b }
  opaque predicate RightFact(c: int, d: int, w: int) { c <= w <= d }
  opaque predicate Joined(a: int, b: int, c: int, d: int, w: int) {
    LeftFact(a,b,w) && RightFact(c,d,w)
  }
  opaque predicate Overlap(a: int, b: int, c: int, d: int) {
    exists w: int :: a <= w <= b && c <= w <= d
  }
}
'''
 stages=['''include "Kernel.dfy"
module Stage1 {
  export Public provides K, Left, Right
  import K = Kernel`Internal
  lemma Left(a: int, b: int, w: int)
    requires a <= w <= b
    ensures K.LeftFact(a,b,w)
  { reveal K.LeftFact(); }
  lemma Right(c: int, d: int, w: int)
    requires c <= w <= d
    ensures K.RightFact(c,d,w)
  { reveal K.RightFact(); }
}
''','''include "Kernel.dfy"
module Stage2 {
  export Public provides K, Join
  import K = Kernel`Internal
  lemma Join(a: int, b: int, c: int, d: int, w: int)
    requires K.LeftFact(a,b,w) && K.RightFact(c,d,w)
    ensures K.Joined(a,b,c,d,w)
  { reveal K.Joined(); }
}
''','''include "Kernel.dfy"
module Stage3 {
  export Shallow provides K, Direct
  export Deep provides K, Finish
  import K = Kernel`Internal
  lemma Direct(a: int, b: int, c: int, d: int, w: int)
    requires a <= w <= b && c <= w <= d
    ensures K.Overlap(a,b,c,d)
  { reveal K.Overlap(); assert exists q: int :: a <= q <= b && c <= q <= d; }
  lemma Finish(a: int, b: int, c: int, d: int, w: int)
    requires K.Joined(a,b,c,d,w)
    ensures K.Overlap(a,b,c,d)
  {
    reveal K.Joined(); reveal K.LeftFact(); reveal K.RightFact(); reveal K.Overlap();
    assert a <= w <= b && c <= w <= d;
    assert exists q: int :: a <= q <= b && c <= q <= d;
  }
}
''']
 spec='  lemma {:induction false} Prove(a: int, b: int, c: int, d: int)\n    requires a <= b && c <= d && a <= d && c <= b\n    ensures K.Overlap(a,b,c,d)\n'
 def proof(depth):
  def chain(w):return f'      End.Direct(a,b,c,d,{w});\n' if depth=='shallow' else f'      S1.Left(a,b,{w});\n      S1.Right(c,d,{w});\n      S2.Join(a,b,c,d,{w});\n      End.Finish(a,b,c,d,{w});\n'
  return '    if a >= c {\n'+chain('a')+'    } else {\n'+chain('c')+'    }\n'
 clients=[('a: int, b: int, c: int, d: int','    requires a <= b && c <= d && a <= d && c <= b\n','K.Overlap(a,b,c,d)','a,b,c,d'),('a: int, b: int, c: int, d: int, shift: int','    requires a <= b && c <= d && a <= d && c <= b\n','K.Overlap(c+shift,d+shift,a+shift,b+shift)','c+shift,d+shift,a+shift,b+shift')]
 return dict(kernel=kernel,stages=stages,spec=spec,proof=proof,clients=clients,args='a,b,c,d',family='interval_witness',instance='intersection-witness-001',lineage='development relational diamond ancestry; witness not supplied as parameter, must satisfy both intervals; offset/swapped second client',variables=['a','b','c','d'],calls={'End.Direct':5,'S1.Left':3,'S1.Right':3,'S2.Join':5,'End.Finish':5},mutations={
  'wrong_witness':lambda b,d:b.replace('a >= c','a < c'),
  'missing_left':lambda b,d:b.replace('      S1.Left(a,b,a);\n','').replace('      S1.Left(a,b,c);\n',''),
  'missing_right':lambda b,d:b.replace('      S1.Right(c,d,a);\n','').replace('      S1.Right(c,d,c);\n',''),
  'mismatched_right':lambda b,d:b.replace('S1.Right(c,d,a)','S1.Right(c,d,d)').replace('S1.Right(c,d,c)','S1.Right(c,d,d)'),
  'missing_join':lambda b,d:b.replace('      S2.Join(a,b,c,d,a);\n','').replace('      S2.Join(a,b,c,d,c);\n','')})

def main():
 (ROOT/'fixtures').mkdir(exist_ok=False);tasks=[];checks=[]
 for prefix,maker in [('offset',sequence),('witness',relational)]:
  f=maker()
  for depth in ['shallow','deep']:
   for sharing in ['shared','separate']:
    tid=f'{prefix}-{depth}-{sharing}'
    mutations=list(f['mutations'])
    if prefix=='witness' and depth=='shallow':mutations=['wrong_witness']
    variants=['reference','empty',*mutations,'weakened_helper_contract']
    if sharing=='separate':variants+=['only_a','only_b']
    if depth=='deep':variants+=['hidden_shortcut']
    for variant in variants:
     files=builder.snapshot(f,depth,sharing,variant);p=ROOT/'fixtures'/tid/variant;p.mkdir(parents=True)
     for n,s in files.items():(p/n).write_text(s)
     expected='success' if variant=='reference' else 'resolution_failure' if variant=='hidden_shortcut' else 'termination_failure' if variant=='nondecreasing_recursion' else 'proof_failure'
     checks.append(dict(task_id=tid,variant=variant,path=str(p.relative_to(ROOT)),expected=expected,source_sha256={n:sha(s) for n,s in files.items()}))
    files=builder.snapshot(f,depth,sharing,'empty')
    tasks.append(dict(task_id=tid,family=f['family'],semantic_instance=f['instance'],lineage=f['lineage'],split='calibration-development',depth=depth,sharing=sharing,entry='All.dfy',editable_files=['HelperA.dfy'] if sharing=='shared' else ['HelperA.dfy','HelperB.dfy'],variables=f['variables'],calls={n:a for n,a in f['calls'].items() if n in ('Prove','End.Base') or (n=='End.Direct' and depth=='shallow') or (depth=='deep' and n!='End.Direct')},source_sha256={n:sha(s) for n,s in files.items()},reference_depth={'provider_critical_path':1 if depth=='shallow' else 3,'shape':'generalized offset induction plus base case' if prefix=='offset' else 'construct common witness; two prerequisite facts join'},reference_depth_not_minimal=True))
 save(ROOT/'tasks.json',tasks);save(ROOT/'checks.json',checks);print(len(tasks),'variants;',len(checks),'controls; zero model calls')
if __name__=='__main__':main()
