include "Kernel.dfy"
include "Ops1.dfy"
include "Ops2.dfy"
include "Api.dfy"
module HelperA {
  import K = Kernel`Public
  import A = Api`Shallow
  import O1 = Ops1`Hidden
  import O2 = Ops2`Hidden
  lemma {:induction false} Prove(m: map<int,int>,k: int,j: int)
    requires k in m && j in m
    ensures K.Swap(K.Swap(m,k,j),k,j)==m
  {A.ObserveSwap(m, k, j);
    var m1 := K.Swap(m, k, j);
    assert k in m1;
    assert j in m1;
    A.ObserveSwap(m1, k, j);
    var m2 := K.Swap(m1, k, j);
    assert m2.Keys == m.Keys;
    forall q | q in m
      ensures q in m2 && m2[q] == m[q]
    {
      if q == k {
        assert m2[q] == m1[j];
        assert m1[j] == m[k];
        assert m2[q] == m[q];
      } else if q == j {
        assert m2[q] == m1[k];
        assert m1[k] == m[j];
        assert m2[q] == m[q];
      } else {
        assert m2[q] == m1[q];
        assert m1[q] == m[q];
        assert m2[q] == m[q];
      }
    }
    A.Equal(m2, m);  }
}
