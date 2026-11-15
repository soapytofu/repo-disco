"""Construct D3-M1 proof-certificate fixtures; no verifier or model execution."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parent
INSTANCE='intersection_or_separation'
REQUIRES='a <= b && c <= d'
ARGS='a,b,c,d'
PARAMS='a: int, b: int, c: int, d: int'
KERNEL='''module Kernel {
  export Public provides LeftFact, RightFact, LeftGap, RightGap, Valid, Decided
  export Internal reveals LeftFact, RightFact, LeftGap, RightGap, Valid, Decided
  opaque predicate LeftFact(a: int, b: int, w: int) { a <= w <= b }
  opaque predicate RightFact(c: int, d: int, w: int) { c <= w <= d }
  opaque predicate LeftGap(b: int, c: int) { b < c }
  opaque predicate RightGap(d: int, a: int) { d < a }
  opaque predicate Valid(a: int, b: int, c: int, d: int, kind: int, w: int) {
    (kind == 0 && a <= w <= b && c <= w <= d) ||
    (kind == -1 && b < c) || (kind == 1 && d < a)
  }
  opaque ghost predicate Decided(a: int, b: int, c: int, d: int) {
    exists kind: int, w: int {:trigger Valid(a,b,c,d,kind,w)} :: Valid(a,b,c,d,kind,w)
  }
}
'''
OPS='''include "Kernel.dfy"
module Ops {
  export Public provides K, Left, Right, Before, After
  import K = Kernel`Internal
  lemma Left(a: int, b: int, w: int)
    requires a <= w <= b
    ensures K.LeftFact(a,b,w)
  { reveal K.LeftFact(); }
  lemma Right(c: int, d: int, w: int)
    requires c <= w <= d
    ensures K.RightFact(c,d,w)
  { reveal K.RightFact(); }
  lemma Before(b: int, c: int)
    requires b < c
    ensures K.LeftGap(b,c)
  { reveal K.LeftGap(); }
  lemma After(d: int, a: int)
    requires d < a
    ensures K.RightGap(d,a)
  { reveal K.RightGap(); }
}
'''
API='''include "Kernel.dfy"
module Api {
  export Proof provides K, Witness, Gap
  export Clients provides K, Choose
  export Hidden provides K, DirectWitness
  import K = Kernel`Internal
  lemma Witness(a: int, b: int, c: int, d: int, w: int)
    requires K.LeftFact(a,b,w) && K.RightFact(c,d,w)
    ensures K.Decided(a,b,c,d)
  {
    reveal K.LeftFact(); reveal K.RightFact(); reveal K.Valid();
    assert K.Valid(a,b,c,d,0,w);
    reveal K.Decided();
    assert exists tag: int, point: int {:trigger K.Valid(a,b,c,d,tag,point)} :: K.Valid(a,b,c,d,tag,point);
  }
  lemma Gap(a: int, b: int, c: int, d: int, kind: int)
    requires (kind == -1 && K.LeftGap(b,c)) || (kind == 1 && K.RightGap(d,a))
    ensures K.Decided(a,b,c,d)
  {
    reveal K.LeftGap(); reveal K.RightGap(); reveal K.Valid();
    assert K.Valid(a,b,c,d,kind,0);
    reveal K.Decided();
    assert exists tag: int, point: int {:trigger K.Valid(a,b,c,d,tag,point)} :: K.Valid(a,b,c,d,tag,point);
  }
  lemma Choose(a: int, b: int, c: int, d: int) returns (kind: int, w: int)
    requires a <= b && c <= d
    requires K.Decided(a,b,c,d)
    ensures kind == -1 || kind == 0 || kind == 1
    ensures kind == 0 ==> a <= w <= b && c <= w <= d
    ensures (kind == 0) == (a <= d && c <= b)
    ensures (kind == -1) == (b < c)
    ensures (kind == 1) == (d < a)
  {
    reveal K.Decided();
    kind, w :| K.Valid(a,b,c,d,kind,w);
    reveal K.Valid();
  }
  lemma DirectWitness(a: int, b: int, c: int, d: int, w: int)
    requires a <= w <= b && c <= w <= d
    ensures K.Decided(a,b,c,d)
  {
    reveal K.Valid(); assert K.Valid(a,b,c,d,0,w);
    reveal K.Decided();
    assert exists tag: int, point: int {:trigger K.Valid(a,b,c,d,tag,point)} :: K.Valid(a,b,c,d,tag,point);
  }
}
'''
REFERENCE='''    if b < c {
      O.Before(b,c);
      A.Gap(a,b,c,d,-1);
    } else if d < a {
      O.After(d,a);
      A.Gap(a,b,c,d,1);
    } else {
      var w := if a < c then c else a;
      O.Left(a,b,w);
      O.Right(c,d,w);
      A.Witness(a,b,c,d,w);
    }
'''
ALTERNATIVE='''    if a <= d && c <= b {
      var w := if b < d then b else d;
      O.Right(c,d,w);
      O.Left(a,b,w);
      A.Witness(a,b,c,d,w);
    } else if c > b {
      O.Before(b,c);
      A.Gap(a,b,c,d,-1);
    } else {
      O.After(d,a);
      A.Gap(a,b,c,d,1);
    }
'''
VARIANTS={
 'reference':(REFERENCE,'success','none'),
 'alternative':(ALTERNATIVE,'success','none'),
 'empty':('','proof_failure','postcondition'),
 'faulty_touching':(REFERENCE.replace('if b < c','if b <= c',1),'proof_failure','precondition'),
 'wrong_witness':(REFERENCE.replace('if a < c then c else a','a'),'proof_failure','precondition'),
 'wrong_orientation':(REFERENCE.replace('A.Gap(a,b,c,d,-1);','A.Gap(a,b,c,d,1);',1),'proof_failure','precondition'),
 'missing_gap_evidence':(REFERENCE.replace('      O.Before(b,c);\n','').replace('      O.After(d,a);\n',''),'proof_failure','precondition'),
 'missing_right_evidence':(REFERENCE.replace('      O.Right(c,d,w);\n',''),'proof_failure','precondition'),
 'no_negative_certificate':(REFERENCE.replace('      O.Before(b,c);\n      A.Gap(a,b,c,d,-1);\n',''),'proof_failure','postcondition'),
 'hidden_shortcut':(REFERENCE.replace('A.Witness(a,b,c,d,w);','A.DirectWitness(a,b,c,d,w);'),'resolution_failure','missing export member'),
}
SIGNATURE='''  lemma {:induction false} Prove(a: int, b: int, c: int, d: int)
    requires a <= b && c <= d
    ensures K.Decided(a,b,c,d)
'''

def helper(name,body,forward=False):
 head='include "Kernel.dfy"\ninclude "Ops.dfy"\ninclude "Api.dfy"\n'
 imports='  import K = Kernel`Public\n  import O = Ops`Public\n  import A = Api`Proof\n'
 if forward:
  head+='include "HelperA.dfy"\n';imports+='  import H = HelperA\n';body='    H.Prove(a,b,c,d);\n'
 return head+'module '+name+' {\n'+imports+SIGNATURE+'  {\n'+body+'  }\n}\n'

def client(name,helper_name,shifted=False):
 params=PARAMS+(', shift: int' if shifted else '')
 a,b,c,d=('c+shift','d+shift','a+shift','b+shift') if shifted else ('a','b','c','d')
 args=','.join((a,b,c,d))
 return ('include "'+helper_name+'.dfy"\ninclude "Api.dfy"\nmodule '+name+' {\n'
 +'  import H = '+helper_name+'\n  import A = Api`Clients\n'
 +'  lemma Target('+params+') returns (kind: int, w: int)\n'
 +'    requires a <= b && c <= d\n'
 +'    ensures kind == -1 || kind == 0 || kind == 1\n'
 +'    ensures kind == 0 ==> '+a+' <= w <= '+b+' && '+c+' <= w <= '+d+'\n'
 +'    ensures (kind == 0) == ('+a+' <= '+d+' && '+c+' <= '+b+')\n'
 +'    ensures (kind == -1) == ('+b+' < '+c+')\n'
 +'    ensures (kind == 1) == ('+d+' < '+a+')\n'
 +'  {\n    H.Prove('+args+');\n    kind, w := A.Choose('+args+');\n  }\n}\n')

def sources(sharing,variant):
 body=VARIANTS[variant][0]
 return {'Kernel.dfy':KERNEL,'Ops.dfy':OPS,'Api.dfy':API,
 'HelperA.dfy':helper('HelperA',body),'HelperB.dfy':helper('HelperB',body,sharing=='shared'),
 'ClientA.dfy':client('ClientA','HelperA'),'ClientB.dfy':client('ClientB','HelperB',True),
 'All.dfy':'include "ClientA.dfy"\ninclude "ClientB.dfy"\n'}

def sha(raw):return hashlib.sha256(raw if isinstance(raw,bytes) else raw.encode()).hexdigest()
def hashes(files):return {n:sha(s) for n,s in sorted(files.items())}
def save(path,value):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,indent=2)+'\n')
def boundary(source):
 start=source.index('  {\n',source.index('lemma {:induction false} Prove'))+len('  {\n');end=source.rindex('  }\n}\n')
 return dict(start=len(source[:start].encode()),end=len(source[:end].encode()),protected_sha256=sha(source[:start]+'<EDITABLE_BODY>\n'+source[end:]))

def build(root=ROOT):
 root=Path(root);root.mkdir(parents=True,exist_ok=True);tasks=[];cases=[]
 for sharing in ('shared','separate'):
  tid=INSTANCE+'-'+sharing;empty=sources(sharing,'empty');editable=['HelperA.dfy']+(['HelperB.dfy'] if sharing=='separate' else [])
  tasks.append(dict(task_id=tid,semantic_instance=INSTANCE,proposal_id='D3-M1',family='constraint_witness',split='development',
   ancestor_group='relational_witnesses',held_out=False,depth='fixed_interface',entry='All.dfy',sharing=sharing,
   editable_files=editable,source_sha256=hashes(empty),body_boundaries={n:boundary(empty[n]) for n in editable},
   params=['a','b','c','d'],calls={'O.Left':3,'O.Right':3,'O.Before':2,'O.After':2,'A.Witness':5,'A.Gap':5},
   pure={'K.LeftFact':3,'K.RightFact':3,'K.LeftGap':2,'K.RightGap':2,'K.Valid':6,'K.Decided':4},self_recursion=False,
   primary_fault='faulty_touching',precondition=REQUIRES,goal='K.Decided(a,b,c,d)',
   outcome_tags={'-1':'b<c; left interval strictly before right','0':'w belongs to both intervals','1':'d<a; right interval strictly before left'},
   client_interface='Ghost lemma returns kind and witness using a protected choice rule; no executable search implementation is claimed.',
   guard_registry_status='pending; proposed environment only',verification_status='not_run',minimum_proof_depth=None))
  for variant,(body,expected,diagnostic) in VARIANTS.items():
   f=sources(sharing,variant);path=Path('fixtures')/tid/variant
   for name,text in f.items():p=root/path/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
   cases.append(dict(case_id=tid+'-'+variant,task_id=tid,variant=variant,path=str(path),entry='All.dfy',expected=expected,
    expected_exit=0 if expected=='success' else 2 if expected=='resolution_failure' else 4,
    expected_diagnostic=diagnostic,primary_diagnostic=None if diagnostic=='none' else 'DirectWitness' if diagnostic=='missing export member' else diagnostic,
    source_sha256=hashes(f),body_boundaries={n:boundary(f[n]) for n in editable}))
  for name,text in empty.items():p=root/'templates'/tid/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
 save(root/'tasks.json',tasks);save(root/'cases.json',cases)
 manifest={str(p.relative_to(root)):sha(p.read_bytes()) for folder in ('fixtures','templates') for p in sorted((root/folder).rglob('*.dfy'))}
 for name in ('tasks.json','cases.json'):manifest[name]=sha((root/name).read_bytes())
 save(root/'fixture-manifest.json',manifest)
 return tasks,cases,manifest
if __name__=='__main__':
 tasks,cases,manifest=build();print(json.dumps(dict(tasks=len(tasks),checks=len(cases),source_files=len(manifest)-2,verified=False,model_calls=0)))
