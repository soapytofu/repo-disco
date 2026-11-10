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
  {var s1 := K.Swap(m,k,j);
    A.ObserveSwap(m,k,j);
    assert k in s1 && j in s1;
    var s2 := K.Swap(s1,k,j);
    A.ObserveSwap(s1,k,j);
    assert s2.Keys == m.Keys;
    forall q | q in m
      ensures q in s2 && s2[q] == m[q]
    {
      assert q in s1;
      assert s1[q] == (if q==k then m[j] else if q==j then m[k] else m[q]);
      assert s2[q] == (if q==k then s1[j] else if q==j then s1[k] else s1[q]);
      if q == k {
        assert s2[q] == s1[j];
        if j == k {
          assert s1[j] == m[j];
          assert s2[q] == m[k];
        } else {
          assert s1[j] == m[k];
          assert s2[q] == m[k];
        }
      } else if q == j {
        assert s2[q] == s1[k];
        if k == j {
          assert s1[k] == m[k];
          assert s2[q] == m[j];
        } else {
          assert s1[k] == m[j];
          assert s2[q] == m[j];
        }
      } else {
        assert s2[q] == s1[q];
        assert s1[q] == m[q];
      }
    }
    A.Equal(s2, m);  }
}
