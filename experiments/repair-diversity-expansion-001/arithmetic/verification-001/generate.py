"""D1-M2 fixed-interface repair fixtures; generation is offline, not validation."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parent
INSTANCE='saturating_assoc'
KERNEL='''module Kernel {
  export Public provides Sat
  export Internal reveals Sat
  opaque function Sat(c: int, x: int, y: int): int
  { if x+y <= c then x+y else c }
}
'''
OPS='''include "Kernel.dfy"
module Ops {
  export Public provides K, Low, High
  export Internal provides K, Low, High, Range
  import K = Kernel`Internal
  lemma Low(c: int, x: int, y: int)
    requires 0 <= c && 0 <= x && 0 <= y && x+y <= c
    ensures K.Sat(c,x,y) == x+y
  { reveal K.Sat(); }
  lemma High(c: int, x: int, y: int)
    requires 0 <= c && 0 <= x && 0 <= y && c <= x+y
    ensures K.Sat(c,x,y) == c
  { reveal K.Sat(); }
  lemma Range(c: int, x: int, y: int)
    requires 0 <= c && 0 <= x && 0 <= y
    ensures 0 <= K.Sat(c,x,y) <= c
  { reveal K.Sat(); }
}
'''
REFERENCE='''    if a+b+d <= c {
      O.Low(c,a,b); O.Low(c,b,d);
      O.Low(c,K.Sat(c,a,b),d); O.Low(c,a,K.Sat(c,b,d));
    } else {
      if a+b <= c { O.Low(c,a,b); }
      else { O.High(c,a,b); }
      O.High(c,K.Sat(c,a,b),d);
      if b+d <= c { O.Low(c,b,d); }
      else { O.High(c,b,d); }
      O.High(c,a,K.Sat(c,b,d));
    }
'''
ALTERNATIVE='''    if a+b <= c {
      O.Low(c,a,b);
      if b+d <= c {
        O.Low(c,b,d);
        if a+b+d <= c {
          O.Low(c,a+b,d); O.Low(c,a,b+d);
        } else {
          O.High(c,a+b,d); O.High(c,a,b+d);
        }
      } else {
        O.High(c,b,d); O.High(c,a+b,d); O.High(c,a,c);
      }
    } else {
      O.High(c,a,b); O.High(c,c,d);
      if b+d <= c { O.Low(c,b,d); O.High(c,a,b+d); }
      else { O.High(c,b,d); O.High(c,a,c); }
    }
'''
FAULTY='''    O.Low(c,a,b); O.Low(c,b,d);
    if a+b+d <= c { O.Low(c,a+b,d); O.Low(c,a,b+d); }
    else { O.High(c,a+b,d); O.High(c,a,b+d); }
'''
TOTAL_ONLY='''    if a+b+d <= c {
      O.Low(c,a,b); O.Low(c,b,d); O.Low(c,a+b,d); O.Low(c,a,b+d);
    } else {
      O.High(c,a,b); O.High(c,b,d); O.High(c,c,d); O.High(c,a,c);
    }
'''
MISSING_RIGHT='''    if a+b <= c { O.Low(c,a,b); }
    else { O.High(c,a,b); }
    if K.Sat(c,a,b)+d <= c { O.Low(c,K.Sat(c,a,b),d); }
    else { O.High(c,K.Sat(c,a,b),d); }
'''
MISSING_OUTER='''    if a+b <= c { O.Low(c,a,b); } else { O.High(c,a,b); }
    if b+d <= c { O.Low(c,b,d); } else { O.High(c,b,d); }
'''
WRONG_BOUNDARY='''    if a <= c { O.Low(c,a,b); }
    else { O.High(c,a,b); }
    if b+d <= c { O.Low(c,b,d); } else { O.High(c,b,d); }
    if a+b+d <= c { O.Low(c,K.Sat(c,a,b),d); O.Low(c,a,K.Sat(c,b,d)); }
    else { O.High(c,K.Sat(c,a,b),d); O.High(c,a,K.Sat(c,b,d)); }
'''
VARIANTS={
 'reference':(REFERENCE,'success',None),
 'alternative':(ALTERNATIVE,'success',None),
 'empty':('','proof_failure','postcondition'),
 'faulty':(FAULTY,'proof_failure','precondition'),
 'saturated_total_only':(TOTAL_ONLY,'proof_failure','precondition'),
 'missing_right':(MISSING_RIGHT,'proof_failure','postcondition'),
 'missing_outer':(MISSING_OUTER,'proof_failure','postcondition'),
 'wrong_boundary':(WRONG_BOUNDARY,'proof_failure','precondition'),
 'hidden_range':('    O.Range(c,a,b);\n','resolution_failure','Range'),
}
SIGNATURE='''  lemma {:induction false} Prove(c: int, a: int, b: int, d: int)
    requires 0 <= c && 0 <= a && 0 <= b && 0 <= d
    ensures K.Sat(c,K.Sat(c,a,b),d) == K.Sat(c,a,K.Sat(c,b,d))
'''
def helper(name,body):
 return 'include "Kernel.dfy"\ninclude "Ops.dfy"\nmodule '+name+' {\n  import K = Kernel`Public\n  import O = Ops`Public\n'+SIGNATURE+'  {\n'+body+'  }\n}\n'
def forward():
 return 'include "Kernel.dfy"\ninclude "HelperA.dfy"\nmodule HelperB {\n  import K = Kernel`Public\n  import H = HelperA\n'+SIGNATURE+'  { H.Prove(c,a,b,d); }\n}\n'
CLIENT_A='''include "Kernel.dfy"
include "HelperA.dfy"
module ClientA {
  import K = Kernel`Public
  import H = HelperA
  lemma Target(c: int, a: int, b: int, d: int)
    requires 0 <= c && 0 <= a && 0 <= b && 0 <= d
    ensures K.Sat(c,K.Sat(c,a,b),d) == K.Sat(c,a,K.Sat(c,b,d))
  { H.Prove(c,a,b,d); }
}
'''
CLIENT_B='''include "Kernel.dfy"
include "HelperB.dfy"
module ClientB {
  import K = Kernel`Public
  import H = HelperB
  lemma Target(c: int, a: int, b: int, d: int, e: int)
    requires 0 <= c && 0 <= a && 0 <= b && 0 <= d && 0 <= e
    ensures K.Sat(c,K.Sat(c,a+b,d),e) == K.Sat(c,a+b,K.Sat(c,d,e))
  { H.Prove(c,a+b,d,e); }
}
'''
def sources(sharing,body):
 return {'Kernel.dfy':KERNEL,'Ops.dfy':OPS,'HelperA.dfy':helper('HelperA',body),
 'HelperB.dfy':forward() if sharing=='shared' else helper('HelperB',body),
 'ClientA.dfy':CLIENT_A,'ClientB.dfy':CLIENT_B,
 'All.dfy':'include "ClientA.dfy"\ninclude "ClientB.dfy"\n'}
def hashes(files):return {n:hashlib.sha256(s.encode()).hexdigest() for n,s in sorted(files.items())}
def save(path,value):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,indent=2)+'\n')
def build(root=ROOT):
 root=Path(root);root.mkdir(parents=True,exist_ok=True);tasks=[];cases=[]
 for sharing in ('shared','separate'):
  tid=INSTANCE+'-'+sharing;empty=sources(sharing,'')
  task=dict(task_id=tid,semantic_instance=INSTANCE,proposal_id='D1-M2',family='conditional_arithmetic',split='development',depth='fixed_interface',sharing=sharing,entry='All.dfy',editable_files=['HelperA.dfy']+(['HelperB.dfy'] if sharing=='separate' else []),source_sha256=hashes(empty),primary_fault='faulty',params=['c','a','b','d'],calls={'O.Low':3,'O.High':3},pure={'K.Sat':3},self_recursion=False)
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
