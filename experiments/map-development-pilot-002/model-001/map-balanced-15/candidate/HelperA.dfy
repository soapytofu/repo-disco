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
  {A.ObserveMerge(m, n);
    A.ObserveRestrict(K.Merge(m, n), keep);
    A.ObserveRestrict(m, keep);
    A.ObserveRestrict(n, keep);
    var left := K.Restrict(K.Merge(m, n), keep);
    var rm := K.Restrict(m, keep);
    var rn := K.Restrict(n, keep);
    assert forall q :: q in rm ==> q !in rn;
    A.ObserveMerge(rm, rn);
    var right := K.Merge(rm, rn);
    assert left.Keys == right.Keys;
    forall q | q in left ensures left[q] == right[q] {
      assert q in K.Merge(m, n);
      assert q in keep;
      if q in m {
        assert left[q] == m[q];
        assert q in rm;
        assert right[q] == rm[q];
        assert rm[q] == m[q];
      } else {
        assert q in n;
        assert left[q] == n[q];
        assert q in rn;
        assert right[q] == rn[q];
        assert rn[q] == n[q];
      }
    }
    A.Equal(left, right);  }
}
