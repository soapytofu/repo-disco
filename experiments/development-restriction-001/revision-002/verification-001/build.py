"""D4-M2 development construction. No verifier or model dispatch."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent

KERNEL='''module Kernel {
  export Public provides Separate, Merge, Restrict
  export Internal reveals Separate, Merge, Restrict
  opaque predicate Separate(m: map<int,int>,n: map<int,int>) {
    forall q :: q in m ==> q !in n
  }
  opaque function Merge(m: map<int,int>,n: map<int,int>): map<int,int> {
    if Separate(m,n) then
      map q | q in m.Keys + n.Keys :: if q in m then m[q] else n[q]
    else map[]
  }
  opaque function Restrict(m: map<int,int>,keep: set<int>): map<int,int> {
    map q | q in m && q in keep :: m[q]
  }
}
'''
OPS1='''include "Kernel.dfy"
module Ops1 {
  export Hidden provides K
  export Public provides K, Certify
  import K = Kernel`Internal
  lemma Certify(m: map<int,int>,n: map<int,int>)
    requires forall q :: q in m ==> q !in n
    ensures K.Separate(m,n)
  { reveal K.Separate(); }
}
'''
OPS2='''include "Kernel.dfy"
module Ops2 {
  export Hidden provides K
  export Public provides K, MergeKeys, MergeAt, RestrictKeys, RestrictAt
  import K = Kernel`Internal
  lemma MergeKeys(m: map<int,int>,n: map<int,int>)
    requires K.Separate(m,n)
    ensures K.Merge(m,n).Keys == m.Keys + n.Keys
  { reveal K.Merge(); }
  lemma MergeAt(m: map<int,int>,n: map<int,int>,q: int)
    requires K.Separate(m,n)
    requires q in m || q in n
    ensures q in K.Merge(m,n)
    ensures K.Merge(m,n)[q] == (if q in m then m[q] else n[q])
  { reveal K.Merge(); }
  lemma RestrictKeys(m: map<int,int>,keep: set<int>)
    ensures K.Restrict(m,keep).Keys == m.Keys - (m.Keys - keep)
  { reveal K.Restrict(); }
  lemma RestrictAt(m: map<int,int>,keep: set<int>,q: int)
    requires q in m && q in keep
    ensures q in K.Restrict(m,keep)
    ensures K.Restrict(m,keep)[q] == m[q]
  { reveal K.Restrict(); }
}
'''
API='''include "Kernel.dfy"
module Api {
  export Shallow provides K, ObserveMerge, ObserveRestrict, Equal
  export Deep provides K, Equal
  import K = Kernel`Internal
  lemma ObserveMerge(m: map<int,int>,n: map<int,int>)
    requires forall q :: q in m ==> q !in n
    ensures K.Merge(m,n).Keys == m.Keys + n.Keys
    ensures forall q :: q in K.Merge(m,n) ==>
      K.Merge(m,n)[q] == (if q in m then m[q] else n[q])
  { reveal K.Separate(); reveal K.Merge(); }
  lemma ObserveRestrict(m: map<int,int>,keep: set<int>)
    ensures K.Restrict(m,keep).Keys == m.Keys - (m.Keys - keep)
    ensures forall q :: q in K.Restrict(m,keep) ==> q in m && K.Restrict(m,keep)[q] == m[q]
  { reveal K.Restrict(); }
  lemma Equal(left: map<int,int>,right: map<int,int>)
    requires left.Keys == right.Keys
    requires forall q :: q in left ==> q in right && left[q] == right[q]
    ensures left == right
  { }
}
'''
SIGNATURE='''  lemma {:induction false} Prove(m: map<int,int>,n: map<int,int>,keep: set<int>)
    requires forall q :: q in m ==> q !in n
    ensures K.Restrict(K.Merge(m,n),keep) == K.Merge(K.Restrict(m,keep),K.Restrict(n,keep))
'''
VARIANTS=['reference','empty','missing_left_value','missing_right_value','wrong_filter',
          'one_sided_values','lost_domain','skip_empty_left','hidden_shortcut']


def hashes(fs):return {n:hashlib.sha256(s.encode()).hexdigest() for n,s in sorted(fs.items())}


def proof(depth,variant):
    if variant=='empty':return ''
    if variant=='hidden_shortcut':
        return '    O1.Certify(m,n);\n' if depth=='shallow' else '    A.ObserveMerge(m,n);\n'
    body='''    var merged := K.Merge(m,n);
    var left := K.Restrict(merged,keep);
    var rm := K.Restrict(m,keep);
    var rn := K.Restrict(n,keep);
    var right := K.Merge(rm,rn);
'''
    if depth=='shallow':
        body+='''    A.ObserveRestrict(m,keep);
    A.ObserveRestrict(n,keep);
    A.ObserveMerge(m,n);
    A.ObserveRestrict(merged,keep);
    A.ObserveMerge(rm,rn);
'''
    else:
        body+='''    O2.RestrictKeys(m,keep); O2.RestrictKeys(n,keep);
    O1.Certify(m,n); O2.MergeKeys(m,n);
    O2.RestrictKeys(merged,keep);
    O1.Certify(rm,rn); O2.MergeKeys(rm,rn);
'''
    body+='''    assert left.Keys == right.Keys;
    forall q | q in left ensures q in right && left[q] == right[q] {
'''
    if depth=='deep':
        body+='''      O2.RestrictAt(merged,keep,q);
      O2.MergeAt(m,n,q);
      O2.MergeAt(rm,rn,q);
      if q in m { O2.RestrictAt(m,keep,q); }
      else { O2.RestrictAt(n,keep,q); }
'''
    body+='''    }
    A.Equal(left,right);
'''
    if variant in ('missing_left_value','missing_right_value'):
        side='m' if variant=='missing_left_value' else 'n'
        text=f'O2.RestrictAt({side},keep,q);' if depth=='deep' else f'    A.ObserveRestrict({side},keep);\n'
        body=body.replace(text,'')
    elif variant=='wrong_filter':
        body=body.replace('O2.RestrictAt(n,keep,q);','O2.RestrictAt(n,{},q);') if depth=='deep' else body.replace('A.ObserveRestrict(n,keep);','A.ObserveRestrict(n,{});')
    elif variant=='one_sided_values':
        body+='    assert forall q :: q in right ==> q in m && right[q] == m[q];\n'
    elif variant=='lost_domain':body+='    assert right.Keys == rm.Keys;\n'
    elif variant=='skip_empty_left':body='    if |m| > 0 {\n'+body+'    }\n'
    elif variant=='missing_certificate':
        assert depth=='deep';body=body.replace('O1.Certify(rm,rn);','')
    elif variant!='reference':raise ValueError(variant)
    return body


def helper(name,depth,body,forward=False):
    if forward:
        return 'include "Kernel.dfy"\ninclude "HelperA.dfy"\nmodule HelperB {\n  import K = Kernel`Public\n  import H = HelperA\n'+SIGNATURE+'  {\n    H.Prove(m,n,keep);\n  }\n}\n'
    view='Public' if depth=='deep' else 'Hidden';api='Deep' if depth=='deep' else 'Shallow'
    return 'include "Kernel.dfy"\ninclude "Ops1.dfy"\ninclude "Ops2.dfy"\ninclude "Api.dfy"\n'+f'module {name} {{\n  import K = Kernel`Public\n  import A = Api`{api}\n  import O1 = Ops1`{view}\n  import O2 = Ops2`{view}\n'+SIGNATURE+'  {\n'+body+'  }\n}\n'


def client(letter):
    head=f'include "Kernel.dfy"\ninclude "Helper{letter}.dfy"\nmodule Client{letter} {{\n  import K = Kernel`Public\n  import H = Helper{letter}\n'
    if letter=='A':return head+SIGNATURE.replace(' {:induction false}','').replace('Prove(','Target(')+'  { H.Prove(m,n,keep); }\n}\n'
    return head+'''  lemma Target(m: map<int,int>,n: map<int,int>,keep: set<int>,q: int)
    requires forall k :: k in m ==> k !in n
    requires q in K.Restrict(K.Merge(m,n),keep)
    ensures q in K.Merge(K.Restrict(m,keep),K.Restrict(n,keep))
    ensures K.Merge(K.Restrict(m,keep),K.Restrict(n,keep))[q] == K.Restrict(K.Merge(m,n),keep)[q]
  { H.Prove(m,n,keep); }
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
            tid=f'merge_restrict-{depth}-{sharing}';seed=sources(depth,sharing,'empty')
            tasks.append(dict(task_id=tid,plan_id='D4-M2',family='finite_map',semantic_instance='merge_restrict',depth=depth,sharing=sharing,
                entry='All.dfy',source_sha256=hashes(seed),editable_files=['HelperA.dfy'] if sharing=='shared' else ['HelperA.dfy','HelperB.dfy'],
                development_only=True,held_out=False,minimum_proof_depth=None,model_calls=0))
            for variant in VARIANTS+(['missing_certificate'] if depth=='deep' else []):
                fs=sources(depth,sharing,variant);rel=f'fixtures/{tid}/{variant}';folder=ROOT/rel;folder.mkdir(parents=True,exist_ok=False)
                for name,text in fs.items():(folder/name).write_text(text)
                expected='success' if variant=='reference' else 'resolution_failure' if variant=='hidden_shortcut' else 'proof_failure'
                checks.append(dict(task_id=tid,variant=variant,path=rel,phase='core' if variant in ('reference','empty') else 'negatives',expected=expected,source_sha256=hashes(fs)))
    for name,data in [('tasks.json',tasks),('checks.json',checks)]:
        with (ROOT/name).open('x') as f:f.write(json.dumps(data,indent=2)+'\n')
    print(json.dumps(dict(semantic_instances=1,workspaces=4,planned_controls=len(checks),model_calls=0,status='CONSTRUCTED_NOT_VERIFIED')))


if __name__=='__main__':build()
