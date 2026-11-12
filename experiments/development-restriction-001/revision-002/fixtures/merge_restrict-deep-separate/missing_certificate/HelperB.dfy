include "Kernel.dfy"
include "Ops1.dfy"
include "Ops2.dfy"
include "Api.dfy"
module HelperB {
  import K = Kernel`Public
  import A = Api`Deep
  import O1 = Ops1`Public
  import O2 = Ops2`Public
  lemma {:induction false} Prove(m: map<int,int>,n: map<int,int>,keep: set<int>)
    requires forall q :: q in m ==> q !in n
    ensures K.Restrict(K.Merge(m,n),keep) == K.Merge(K.Restrict(m,keep),K.Restrict(n,keep))
  {
    var merged := K.Merge(m,n);
    var left := K.Restrict(merged,keep);
    var rm := K.Restrict(m,keep);
    var rn := K.Restrict(n,keep);
    var right := K.Merge(rm,rn);
    O2.RestrictKeys(m,keep); O2.RestrictKeys(n,keep);
    O1.Certify(m,n); O2.MergeKeys(m,n);
    O2.RestrictKeys(merged,keep);
     O2.MergeKeys(rm,rn);
    assert left.Keys == right.Keys;
    forall q | q in left ensures q in right && left[q] == right[q] {
      O2.RestrictAt(merged,keep,q);
      O2.MergeAt(m,n,q);
      O2.MergeAt(rm,rn,q);
      if q in m { O2.RestrictAt(m,keep,q); }
      else { O2.RestrictAt(n,keep,q); }
    }
    A.Equal(left,right);
  }
}
