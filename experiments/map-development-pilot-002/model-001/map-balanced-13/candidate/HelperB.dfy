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
    forall q1 | q1 in left ensures left[q1] == right[q1] {
      assert q1 in K.Merge(m, n);
      assert K.Merge(m, n)[q1] == (if q1 in m then m[q1] else n[q1]);
      assert left[q1] == K.Merge(m, n)[q1];
      if q1 in m {
        assert q1 in K.Restrict(m, keep);
        assert right[q1] == K.Restrict(m, keep)[q1];
        assert K.Restrict(m, keep)[q1] == m[q1];
      } else {
        assert q1 in n;
        assert q1 in K.Restrict(n, keep);
        assert right[q1] == K.Restrict(n, keep)[q1];
        assert K.Restrict(n, keep)[q1] == n[q1];
      }
    }
    A.Equal(left, right);  }
}
