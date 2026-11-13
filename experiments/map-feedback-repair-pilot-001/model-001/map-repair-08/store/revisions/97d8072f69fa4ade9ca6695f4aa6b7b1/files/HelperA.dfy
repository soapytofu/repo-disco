include "Kernel.dfy"
include "Ops1.dfy"
include "Ops2.dfy"
include "Api.dfy"
module HelperA {
  import K = Kernel`Public
  import A = Api`Deep
  import O1 = Ops1`Public
  import O2 = Ops2`Public
  lemma {:induction false} Prove(m: map<int,int>,n: map<int,int>,keep: set<int>)
    requires forall q :: q in m ==> q !in n
    ensures K.Restrict(K.Merge(m,n),keep) == K.Merge(K.Restrict(m,keep),K.Restrict(n,keep))
  {O1.Certify(m, n);
    O2.RestrictKeys(m, keep);
    O2.RestrictKeys(n, keep);
    O2.MergeKeys(m, n);
    O2.RestrictKeys(K.Merge(m, n), keep);
    var rm := K.Restrict(m, keep);
    var rn := K.Restrict(n, keep);
    assert forall q1 :: q1 in rm ==> q1 in m;
    assert forall q2 :: q2 in rn ==> q2 in n;
    assert forall q3 :: q3 in rm ==> q3 !in rn;
    O1.Certify(rm, rn);
    O2.MergeKeys(rm, rn);
    var left := K.Restrict(K.Merge(m, n), keep);
    var right := K.Merge(rm, rn);
    assert left.Keys == right.Keys;
    forall q0 | q0 in left ensures (q0 in right) && (left[q0] == right[q0]) {
      if q0 in m {
        O2.MergeAt(m, n, q0);
        O2.RestrictAt(K.Merge(m, n), keep, q0);
        O2.RestrictAt(m, keep, q0);
        O2.MergeAt(rm, rn, q0);
        assert left[q0] == right[q0];
      } else {
        O2.MergeAt(m, n, q0);
        O2.RestrictAt(K.Merge(m, n), keep, q0);
        O2.RestrictAt(n, keep, q0);
        O2.MergeAt(rm, rn, q0);
        assert left[q0] == right[q0];
      }
    }
    A.Equal(left, right);  }
}
