include "Kernel.dfy"
include "Ops1.dfy"
include "Ops2.dfy"
include "Api.dfy"
module HelperA {
  import K = Kernel`Public
  import A = Api`Shallow
  import O1 = Ops1`Hidden
  import O2 = Ops2`Hidden
  lemma {:induction false} Prove(m: map<int,int>,n: map<int,int>,keep: set<int>)
    requires forall q :: q in m ==> q !in n
    ensures K.Restrict(K.Merge(m,n),keep) == K.Merge(K.Restrict(m,keep),K.Restrict(n,keep))
  {
    var merged := K.Merge(m,n);
    var left := K.Restrict(merged,keep);
    var rm := K.Restrict(m,keep);
    var rn := K.Restrict(n,keep);
    var right := K.Merge(rm,rn);
    A.ObserveRestrict(m,keep);
    A.ObserveRestrict(n,keep);
    A.ObserveMerge(m,n);
    A.ObserveRestrict(merged,keep);
    A.ObserveMerge(rm,rn);
    assert left.Keys == right.Keys;
    forall q | q in left ensures q in right && left[q] == right[q] {
    }
    A.Equal(left,right);
    assert forall q :: q in right ==> q in m && right[q] == m[q];
  }
}
