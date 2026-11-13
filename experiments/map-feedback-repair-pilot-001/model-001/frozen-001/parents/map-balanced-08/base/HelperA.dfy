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
    O1.Certify(K.Restrict(m, keep), K.Restrict(n, keep));
    O2.RestrictKeys(m, keep);
    O2.RestrictKeys(n, keep);
    O2.MergeKeys(m, n);
    O2.RestrictKeys(K.Merge(m, n), keep);
    O2.MergeKeys(K.Restrict(m, keep), K.Restrict(n, keep));
    var left := K.Restrict(K.Merge(m, n), keep);
    var right := K.Merge(K.Restrict(m, keep), K.Restrict(n, keep));
    forall q0 | q0 in left ensures q0 in right && left[q0] == right[q0] {
      O2.RestrictAt(K.Merge(m, n), keep, q0);
      O2.MergeAt(m, n, q0);
      if q0 in m {
        O2.RestrictAt(m, keep, q0);
        O2.MergeAt(K.Restrict(m, keep), K.Restrict(n, keep), q0);
      } else {
        O2.RestrictAt(n, keep, q0);
        O2.MergeAt(K.Restrict(m, keep), K.Restrict(n, keep), q0);
      }
    }
    forall q1 | q1 in right ensures q1 in left && right[q1] == left[q1] {
      O2.MergeAt(K.Restrict(m, keep), K.Restrict(n, keep), q1);
      if q1 in K.Restrict(m, keep) {
        O2.RestrictAt(m, keep, q1);
        O2.MergeAt(m, n, q1);
        O2.RestrictAt(K.Merge(m, n), keep, q1);
      } else {
        O2.RestrictAt(n, keep, q1);
        O2.MergeAt(m, n, q1);
        O2.RestrictAt(K.Merge(m, n), keep, q1);
      }
    }
    A.Equal(left, right);  }
}
