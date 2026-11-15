"""D2-M1 fixed-interface repair fixtures; offline generation, not verification."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parent
INSTANCE='compression_fixed_point'
KERNEL='''module Kernel {
  export Public provides Compress, Clean
  export Internal reveals Compress, Clean
  opaque function Compress(s: seq<int>): seq<int>
    decreases |s|
  {
    if |s| < 2 then s
    else if s[0] == s[1] then Compress(s[1..])
    else [s[0]] + Compress(s[1..])
  }
  opaque ghost predicate Clean(s: seq<int>)
    decreases |s|
  { |s| < 2 || (s[0] != s[1] && Clean(s[1..])) }
}
'''
OPS='''include "Kernel.dfy"
module Ops {
  export Public provides K, Base, TailInvariant, Boundary, Keep
  export Internal provides K, Base, TailInvariant, Boundary, Keep, Drop
  import K = Kernel`Internal
  lemma Base(s: seq<int>)
    requires |s| < 2
    ensures K.Compress(s) == s
  { reveal K.Compress(); }
  lemma TailInvariant(s: seq<int>)
    requires K.Clean(s) && 2 <= |s|
    ensures K.Clean(s[1..])
  { reveal K.Clean(); }
  lemma Boundary(s: seq<int>)
    requires K.Clean(s) && 2 <= |s|
    ensures s[0] != s[1]
  { reveal K.Clean(); }
  lemma Keep(s: seq<int>)
    requires 2 <= |s| && s[0] != s[1]
    ensures K.Compress(s) == [s[0]] + K.Compress(s[1..])
  { reveal K.Compress(); }
  lemma Drop(s: seq<int>)
    requires 2 <= |s| && s[0] == s[1]
    ensures K.Compress(s) == K.Compress(s[1..])
  { reveal K.Compress(); }
}
'''
INVARIANT='''include "Kernel.dfy"
module Invariant {
  export Public provides K, OutputClean
  import K = Kernel`Internal
  lemma {:induction false} First(s: seq<int>)
    requires 0 < |s|
    ensures 0 < |K.Compress(s)| && K.Compress(s)[0] == s[0]
    decreases |s|
  {
    reveal K.Compress();
    if |s| < 2 {
      assert |s| == 1;
      assert K.Compress(s) == s;
    } else if s[0] == s[1] {
      var rest := s[1..];
      assert 0 < |rest|;
      First(rest);
      assert rest[0] == s[1];
      assert K.Compress(s) == K.Compress(rest);
    } else {
      assert K.Compress(s) == [s[0]] + K.Compress(s[1..]);
    }
  }
  lemma {:induction false} OutputClean(s: seq<int>)
    ensures K.Clean(K.Compress(s))
    decreases |s|
  {
    reveal K.Compress();
    reveal K.Clean();
    if |s| < 2 {
      assert K.Compress(s) == s;
      assert K.Clean(s);
    } else {
      var rest := s[1..];
      assert 0 < |rest|;
      assert rest[0] == s[1];
      OutputClean(rest);
      if s[0] == s[1] {
        assert K.Compress(s) == K.Compress(rest);
      } else {
        First(rest);
        var compressed := K.Compress(rest);
        assert 0 < |compressed| && compressed[0] == s[1];
        assert K.Clean(compressed);
        assert K.Compress(s) == [s[0]] + compressed;
        assert ([s[0]] + compressed)[1..] == compressed;
        assert ([s[0]] + compressed)[0] == s[0];
        assert ([s[0]] + compressed)[1] == compressed[0];
        assert K.Clean([s[0]] + compressed);
      }
      assert K.Clean(K.Compress(s));
    }
  }
}
'''
REFERENCE='''    if |s| < 2 {
      O.Base(s);
    } else {
      O.TailInvariant(s);
      Prove(s[1..]);
      O.Boundary(s);
      O.Keep(s);
      assert s == [s[0]] + s[1..];
    }
'''
ALTERNATIVE='''    if |s| == 0 {
      O.Base(s);
    } else if |s| == 1 {
      O.Base(s);
    } else {
      var rest := s[1..];
      O.Boundary(s);
      O.Keep(s);
      O.TailInvariant(s);
      Prove(rest);
      assert s == [s[0]] + rest;
      assert K.Compress(s) == [s[0]] + K.Compress(rest);
    }
'''
FAULTY='''    if |s| < 2 {
      O.Base(s);
    } else {
      Prove(s[1..]);
      O.Boundary(s); O.Keep(s);
      assert s == [s[0]] + s[1..];
    }
'''
MISSING_BOUNDARY='''    if |s| < 2 { O.Base(s); }
    else {
      O.TailInvariant(s); Prove(s[1..]); O.Keep(s);
      assert s == [s[0]] + s[1..];
    }
'''
NO_RECURSION='''    if |s| < 2 { O.Base(s); }
    else {
      O.TailInvariant(s); O.Boundary(s); O.Keep(s);
      assert s == [s[0]] + s[1..];
    }
'''
WRONG_RECURSION='''    if |s| < 2 { O.Base(s); }
    else {
      O.TailInvariant(s); O.Boundary(s); O.Keep(s);
      Prove(s[2..]);
      assert s == [s[0]] + s[1..];
    }
'''
BAD_BASE='''    if |s| <= 2 { O.Base(s); }
    else {
      O.TailInvariant(s); Prove(s[1..]); O.Boundary(s); O.Keep(s);
      assert s == [s[0]] + s[1..];
    }
'''
NONDECREASING='''    if |s| < 2 { O.Base(s); }
    else { Prove(s); }
'''
VARIANTS={
 'reference':(REFERENCE,'success',None),
 'alternative':(ALTERNATIVE,'success',None),
 'empty':('','proof_failure','postcondition'),
 'faulty':(FAULTY,'proof_failure','precondition'),
 'missing_boundary':(MISSING_BOUNDARY,'proof_failure','precondition'),
 'no_recursion':(NO_RECURSION,'proof_failure','postcondition'),
 'wrong_recursive_argument':(WRONG_RECURSION,'proof_failure','precondition'),
 'bad_base':(BAD_BASE,'proof_failure','precondition'),
 'nondecreasing':(NONDECREASING,'termination_failure','decreases'),
 'hidden_drop':('    if 2 <= |s| { O.Drop(s); }\n','resolution_failure','Drop'),
}
SIGNATURE='''  lemma {:induction false} Prove(s: seq<int>)
    requires K.Clean(s)
    ensures K.Compress(s) == s
    decreases |s|
'''
def helper(name,body):
 return 'include "Kernel.dfy"\ninclude "Ops.dfy"\nmodule '+name+' {\n  import K = Kernel`Public\n  import O = Ops`Public\n'+SIGNATURE+'  {\n'+body+'  }\n}\n'
def forward():
 return 'include "Kernel.dfy"\ninclude "HelperA.dfy"\nmodule HelperB {\n  import K = Kernel`Public\n  import H = HelperA\n'+SIGNATURE+'  { H.Prove(s); }\n}\n'
CLIENT_A='''include "Kernel.dfy"
include "Invariant.dfy"
include "HelperA.dfy"
module ClientA {
  import K = Kernel`Public
  import I = Invariant`Public
  import H = HelperA
  lemma Target(s: seq<int>)
    ensures K.Compress(K.Compress(s)) == K.Compress(s)
  {
    I.OutputClean(s);
    H.Prove(K.Compress(s));
  }
}
'''
CLIENT_B='''include "Kernel.dfy"
include "Invariant.dfy"
include "HelperB.dfy"
module ClientB {
  import K = Kernel`Public
  import I = Invariant`Public
  import H = HelperB
  lemma Target(u: seq<int>, v: seq<int>)
    ensures K.Compress(K.Compress(u+v)) == K.Compress(u+v)
  {
    I.OutputClean(u+v);
    H.Prove(K.Compress(u+v));
  }
}
'''
def sources(sharing,body):
 return {'Kernel.dfy':KERNEL,'Ops.dfy':OPS,'Invariant.dfy':INVARIANT,'HelperA.dfy':helper('HelperA',body),
 'HelperB.dfy':forward() if sharing=='shared' else helper('HelperB',body),
 'ClientA.dfy':CLIENT_A,'ClientB.dfy':CLIENT_B,
 'All.dfy':'include "ClientA.dfy"\ninclude "ClientB.dfy"\n'}
def hashes(files):return {n:hashlib.sha256(s.encode()).hexdigest() for n,s in sorted(files.items())}
def save(path,value):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,indent=2)+'\n')
def build(root=ROOT):
 root=Path(root);root.mkdir(parents=True,exist_ok=True);tasks=[];cases=[]
 for sharing in ('shared','separate'):
  tid=INSTANCE+'-'+sharing;empty=sources(sharing,'')
  task=dict(task_id=tid,semantic_instance=INSTANCE,proposal_id='D2-M1',family='sequence_structure',split='development',depth='fixed_interface',sharing=sharing,entry='All.dfy',editable_files=['HelperA.dfy']+(['HelperB.dfy'] if sharing=='separate' else []),source_sha256=hashes(empty),primary_fault='faulty',params=['s'],calls={'O.Base':1,'O.TailInvariant':1,'O.Boundary':1,'O.Keep':1,'Prove':1},pure={'K.Compress':1,'K.Clean':1},self_recursion=True,
   design='Clients obtain protected output cleanliness then invoke the editable inductive clean-sequence fixed-point lemma; they prove idempotence on original and concatenated inputs.')
  tasks.append(task)
  for variant,(body,expected,diagnostic) in VARIANTS.items():
   files=sources(sharing,body);path=Path('fixtures')/tid/variant
   for name,text in files.items():p=root/path/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
   cases.append(dict(case_id=tid+'-'+variant,task_id=tid,variant=variant,path=str(path),source_sha256=hashes(files),expected=expected,primary_diagnostic=diagnostic))
 save(root/'tasks.json',tasks);save(root/'cases.json',cases)
 manifest={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((root/'fixtures').rglob('*.dfy'))}
 for name in ('tasks.json','cases.json'):manifest[name]=hashlib.sha256((root/name).read_bytes()).hexdigest()
 save(root/'fixture-manifest.json',manifest)
 return tasks,cases,manifest
if __name__=='__main__':
 tasks,cases,manifest=build();print(json.dumps(dict(tasks=len(tasks),checks=len(cases),fixture_files=len(manifest)-2,model_calls=0,verified=False)))
