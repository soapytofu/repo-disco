"""Three new development instances and deliberate repair seeds; no model code."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parent

def sha(b):return hashlib.sha256(b).hexdigest()
def hashes(files):return {n:sha(s.encode()) for n,s in sorted(files.items())}
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n')

THRESHOLD_KERNEL='''module Kernel {
  export Public provides Cut
  export Internal reveals Cut
  opaque function Cut(t: int, x: int): int { if x <= t then 0 else x-t }
}
'''
THRESHOLD_OPS='''include "Kernel.dfy"
module Ops {
  export Public provides K, Below, Above
  import K = Kernel`Internal
  lemma Below(t: int, x: int)
    requires x <= t
    ensures K.Cut(t,x) == 0
  { reveal K.Cut(); }
  lemma Above(t: int, x: int)
    requires t < x
    ensures K.Cut(t,x) == x-t
  { reveal K.Cut(); }
}
'''
THRESHOLD_REFERENCE='''
    if x <= t {
      O.Below(t,x); O.Below(s,0); O.Below(s+t,x);
    } else if x <= s+t {
      O.Above(t,x); O.Below(s,x-t); O.Below(s+t,x);
    } else {
      O.Above(t,x); O.Above(s,x-t); O.Above(s+t,x);
    }
'''
THRESHOLD_ALT='''
    if x > s+t {
      O.Above(t,x); O.Above(s,x-t); O.Above(s+t,x);
    } else if x > t {
      O.Above(t,x); O.Below(s,x-t); O.Below(s+t,x);
    } else {
      O.Below(t,x); O.Below(s,0); O.Below(s+t,x);
    }
'''
THRESHOLD_FAULT='''
    if x <= t {
      O.Below(t,x); O.Below(s,0); O.Below(s+t,x);
    } else {
      O.Above(t,x); O.Above(s,x-t); O.Above(s+t,x);
    }
'''
WITNESS_KERNEL='''module Kernel {
  export Public provides InRange, Feasible
  export Internal reveals InRange, Feasible
  opaque predicate InRange(a: int, b: int, u: int) { a <= u <= b }
  opaque predicate Feasible(a: int, b: int, e: int) {
    exists u: int :: a <= u <= b && u != e
  }
}
'''
WITNESS_OPS='''include "Kernel.dfy"
module Ops {
  export Public provides K, Bounds
  import K = Kernel`Internal
  lemma Bounds(a: int, b: int, u: int)
    requires a <= u <= b
    ensures K.InRange(a,b,u)
  { reveal K.InRange(); }
}
'''
WITNESS_API='''include "Kernel.dfy"
module Api {
  export Public provides K, Finish
  import K = Kernel`Internal
  lemma Finish(a: int, b: int, e: int, u: int)
    requires K.InRange(a,b,u) && u != e
    ensures K.Feasible(a,b,e)
  {
    reveal K.InRange(); reveal K.Feasible();
    assert a <= u <= b && u != e;
  }
}
'''
WITNESS_REFERENCE='''
    var u := if a == e then a+1 else a;
    O.Bounds(a,b,u);
    assert u != e;
    A.Finish(a,b,e,u);
'''
WITNESS_ALT='''
    if a != e {
      O.Bounds(a,b,a); assert a != e; A.Finish(a,b,e,a);
    } else {
      var v := a+1;
      O.Bounds(a,b,v); assert v != e; A.Finish(a,b,e,v);
    }
'''
WEAVE_KERNEL='''module Kernel {
  export Public provides Weave, Left, Right
  export Internal reveals Weave, Left, Right
  opaque function Weave(s: seq<int>, t: seq<int>): seq<int>
    decreases |s|
  {
    if |s| == 0 || |t| == 0 then []
    else [s[0],t[0]] + Weave(s[1..],t[1..])
  }
  opaque function Left(u: seq<int>): seq<int>
    decreases |u|
  { if |u| < 2 then [] else [u[0]] + Left(u[2..]) }
  opaque function Right(u: seq<int>): seq<int>
    decreases |u|
  { if |u| < 2 then [] else [u[1]] + Right(u[2..]) }
}
'''
WEAVE_OPS='''include "Kernel.dfy"
module Ops {
  export Public provides K, Unfold
  import K = Kernel`Internal
  lemma Unfold(s: seq<int>, t: seq<int>)
    requires |s| > 0 && |t| > 0
    ensures K.Weave(s,t) == [s[0],t[0]] + K.Weave(s[1..],t[1..])
  { reveal K.Weave(); }
}
'''
WEAVE_API='''include "Kernel.dfy"
module Api {
  export Public provides K, Empty, Project
  import K = Kernel`Internal
  lemma Empty(s: seq<int>, t: seq<int>)
    requires |s| == 0 && |t| == 0
    ensures K.Weave(s,t) == [] && K.Left([]) == [] && K.Right([]) == []
  { reveal K.Weave(); reveal K.Left(); reveal K.Right(); }
  lemma Project(x: int, y: int, u: seq<int>)
    ensures K.Left([x,y]+u) == [x]+K.Left(u)
    ensures K.Right([x,y]+u) == [y]+K.Right(u)
  { reveal K.Left(); reveal K.Right(); }
}
'''
WEAVE_REFERENCE='''
    if |s| == 0 {
      A.Empty(s,t);
    } else {
      O.Unfold(s,t);
      A.Project(s[0],t[0],K.Weave(s[1..],t[1..]));
      Prove(s[1..],t[1..]);
      assert s == [s[0]] + s[1..];
      assert t == [t[0]] + t[1..];
    }
'''
WEAVE_ALT='''
    if |s| > 0 {
      Prove(s[1..],t[1..]);
      assert s == [s[0]] + s[1..];
      assert t == [t[0]] + t[1..];
      A.Project(s[0],t[0],K.Weave(s[1..],t[1..]));
      O.Unfold(s,t);
    } else { A.Empty(s,t); }
'''
DEFINITIONS={
 'threshold_compose':dict(plan_id='D1-M1',family='conditional_arithmetic',ancestor_group='clamp_soft_threshold_development',
  signature='s: int, t: int, x: int',requires='0 <= s && 0 <= t',goal='K.Cut(s,K.Cut(t,x)) == K.Cut(s+t,x)',args='s,t,x',
  client_b_args='t,s,x',client_b_goal='K.Cut(t,K.Cut(s,x)) == K.Cut(t+s,x)',
  providers={'Kernel.dfy':THRESHOLD_KERNEL,'Ops.dfy':THRESHOLD_OPS},
  reference=THRESHOLD_REFERENCE,alternative=THRESHOLD_ALT,faulty=THRESHOLD_FAULT,
  targeted_1=THRESHOLD_REFERENCE.replace('if x <= t','if x < t'),
  targeted_2=THRESHOLD_REFERENCE.replace('O.Below(s+t,x);',''),
  primary_diagnostic='precondition',failure_type='wrong intermediate saturation case',
  depth_annotation='Case-dependent contract observations compose through Cut(t,x); no minimum-depth or cross-family numeric depth claim.'),
 'excluded_witness':dict(plan_id='D3-M2',family='constraint_witness',ancestor_group='integer_interval_witness_development',
  signature='a: int, b: int, e: int',requires='a < b',goal='K.Feasible(a,b,e)',args='a,b,e',
  client_b_args='a+1,b+1,e+1',client_b_goal='K.Feasible(a+1,b+1,e+1)',
  providers={'Kernel.dfy':WITNESS_KERNEL,'Ops.dfy':WITNESS_OPS,'Api.dfy':WITNESS_API},
  reference=WITNESS_REFERENCE,alternative=WITNESS_ALT,
  faulty=WITNESS_REFERENCE.replace('if a == e then a+1 else a','a'),
  targeted_1=WITNESS_REFERENCE.replace('if a == e then a+1 else a','b+1'),
  targeted_2=WITNESS_REFERENCE.replace('    O.Bounds(a,b,u);\n',''),
  primary_diagnostic='assertion',failure_type='invalid excluded-endpoint witness',
  depth_annotation='Bounds establishes InRange consumed by Finish: two reference contract stages, one edge. Easy semantic contrast, not a harder-task claim.'),
 'weave_unweave':dict(plan_id='D2-M2',family='sequence_structure',ancestor_group='sequence_structural_induction_development',
  signature='s: seq<int>, t: seq<int>',requires='|s| == |t|',goal='K.Left(K.Weave(s,t)) == s && K.Right(K.Weave(s,t)) == t',args='s,t',
  client_b_args='t,s',client_b_goal='K.Left(K.Weave(t,s)) == t && K.Right(K.Weave(t,s)) == s',
  providers={'Kernel.dfy':WEAVE_KERNEL,'Ops.dfy':WEAVE_OPS,'Api.dfy':WEAVE_API},
  reference=WEAVE_REFERENCE,alternative=WEAVE_ALT,faulty=WEAVE_REFERENCE.replace('      Prove(s[1..],t[1..]);\n',''),
  targeted_1=WEAVE_REFERENCE.replace('A.Project(s[0],t[0],','A.Project(t[0],s[0],'),
  targeted_2=WEAVE_REFERENCE.replace('Prove(s[1..],t[1..]);','Prove(s,t);'),
  primary_diagnostic='postcondition',failure_type='missing inductive hypothesis for paired tails',
  depth_annotation='Unfold and paired projection plus an unbounded structural self-call; no scalar shallow/deep comparison across families.')
}

def workspace(instance,sharing,body):
    d=DEFINITIONS[instance];fs=dict(d['providers'])
    includes='include "Kernel.dfy"\ninclude "Ops.dfy"\n'+('include "Api.dfy"\n' if 'Api.dfy' in fs else '')
    imports='  import K = Kernel`Public\n  import O = Ops`Public\n'+('  import A = Api`Public\n' if 'Api.dfy' in fs else '')
    signature='  lemma {:induction false} Prove('+d['signature']+')\n    requires '+d['requires']+'\n    ensures '+d['goal']+'\n'
    if instance=='weave_unweave':signature+='    decreases |s|\n'
    for name in ('HelperA','HelperB'):
        if sharing=='shared' and name=='HelperB':
            fs[name+'.dfy']='include "HelperA.dfy"\nmodule HelperB {\n  import K = Kernel`Public\n  import H = HelperA\n'+signature+'  { H.Prove('+d['args']+'); }\n}\n'
        else:fs[name+'.dfy']=includes+'module '+name+' {\n'+imports+signature+'  {'+body+'  }\n}\n'
    for name,helper,args,goal in [('ClientA','HelperA',d['args'],d['goal']),('ClientB','HelperB',d['client_b_args'],d['client_b_goal'])]:
        fs[name+'.dfy']='include "'+helper+'.dfy"\nmodule '+name+' {\n  import K = Kernel`Public\n  import H = '+helper+'\n  lemma {:induction false} Target('+d['signature']+')\n    requires '+d['requires']+'\n    ensures '+goal+'\n  { H.Prove('+args+'); }\n}\n'
    fs['All.dfy']='include "ClientA.dfy"\ninclude "ClientB.dfy"\n'
    return fs

def generate(root):
    tasks=[];cases=[]
    for instance,d in DEFINITIONS.items():
        for sharing in ('shared','separate'):
            tid=instance+'-'+sharing;template=workspace(instance,sharing,'\n')
            task=dict(task_id=tid,semantic_instance=instance,sharing=sharing,depth='fixed_interface',plan_id=d['plan_id'],family=d['family'],
                ancestor_group=d['ancestor_group'],held_out=False,development_only=True,failure_origin='analyst_constructed',failure_type=d['failure_type'],
                depth_annotation=d['depth_annotation'],entry='All.dfy',editable_files=['HelperA.dfy']+(['HelperB.dfy'] if sharing=='separate' else []),
                source_sha256=hashes(template))
            tasks.append(task)
            for variant in ('reference','faulty','empty','alternative','targeted_1','targeted_2'):
                fs=workspace(instance,sharing,'\n' if variant=='empty' else d[variant]);folder=root/'fixtures'/tid/variant;folder.mkdir(parents=True)
                for n,s in fs.items():(folder/n).write_text(s)
                expected='success' if variant in ('reference','alternative') else ('termination' if instance=='weave_unweave' and variant=='targeted_2' else 'proof_failure')
                cases.append(dict(case_id=tid+'-'+variant,task_id=tid,variant=variant,path=str(folder.relative_to(root)),source_sha256=hashes(fs),
                    expected=expected,expected_exit=0 if expected=='success' else 4,primary_diagnostic=d['primary_diagnostic'] if variant=='faulty' else None))
            folder=root/'templates'/tid;folder.mkdir(parents=True)
            for n,s in template.items():(folder/n).write_text(s)
    save(root/'tasks.json',tasks);save(root/'cases.json',cases)

if __name__=='__main__':generate(ROOT)
