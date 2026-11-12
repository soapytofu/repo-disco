include "Kernel.dfy"
include "Ops1.dfy"
include "Ops2.dfy"
include "Api.dfy"
module HelperB {
  import K = Kernel`Public
  import A = Api`Shallow
  import O1 = Ops1`Hidden
  import O2 = Ops2`Hidden
  lemma {:induction false} Prove(m: map<int,int>,n: map<int,int>,keep: set<int>)
    requires forall q :: q in m ==> q !in n
    ensures K.Restrict(K.Merge(m,n),keep) == K.Merge(K.Restrict(m,keep),K.Restrict(n,keep))
  {A.ObserveMerge(m, n);
    A.ObserveRestrict(K.Merge(m, n), keep);
    A.ObserveRestrict(m, keep);
    A.ObserveRestrict(n, keep);
    A.ObserveMerge(K.Restrict(m, keep), K.Restrict(n, keep));
    var left := K.Restrict(K.Merge(m, n), keep);
    var right := K.Merge(K.Restrict(m, keep), K.Restrict(n, keep));
    assert left.Keys == right.Keys;
    forall q0 | q0 in left ensures left[q0] == right[q0] {
      assert q0 in K.Merge(m, n);
      assert K.Merge(m, n)[q0] == (if q0 in m then m[q0] else n[q0]);
      if q0 in m {
        assert q0 in K.Restrict(m, keep);
        assert K.Restrict(m, keep)[q0] == m[q0];
        assert right[q0] == m[q0];
      } else {
        assert q0 in n;
        assert q0 in K.Restrict(n, keep);
        assert K.Restrict(n, keep)[q0] == n[q0];
        assert right[q0] == n[q0];
      }
    }
    A.Equal(left, right);  }
}
