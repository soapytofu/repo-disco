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
    O1.Certify(K.Restrict(m, keep), K.Restrict(n, keep));
    O2.MergeKeys(m, n);
    O2.RestrictKeys(K.Merge(m, n), keep);
    O2.MergeKeys(K.Restrict(m, keep), K.Restrict(n, keep));
    var left := K.Restrict(K.Merge(m, n), keep);
    var right := K.Merge(K.Restrict(m, keep), K.Restrict(n, keep));
    forall key0 | key0 in left ensures key0 in right && left[key0] == right[key0] {
      O2.RestrictAt(K.Merge(m, n), keep, key0);
      O2.MergeAt(m, n, key0);
      if key0 in m {
        O2.RestrictAt(m, keep, key0);
        O2.MergeAt(K.Restrict(m, keep), K.Restrict(n, keep), key0);
      } else {
        O2.RestrictAt(n, keep, key0);
        O2.MergeAt(K.Restrict(m, keep), K.Restrict(n, keep), key0);
      }
    }
    forall key1 | key1 in right ensures key1 in left && right[key1] == left[key1] {
      O2.MergeAt(K.Restrict(m, keep), K.Restrict(n, keep), key1);
      if key1 in K.Restrict(m, keep) {
        O2.RestrictAt(m, keep, key1);
        O2.MergeAt(m, n, key1);
        O2.RestrictAt(K.Merge(m, n), keep, key1);
      } else {
        O2.RestrictAt(n, keep, key1);
        O2.MergeAt(m, n, key1);
        O2.RestrictAt(K.Merge(m, n), keep, key1);
      }
    }
    A.Equal(left, right);  }
}
