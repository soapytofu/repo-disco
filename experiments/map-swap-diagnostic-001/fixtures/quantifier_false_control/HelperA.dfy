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
  {assert forall fresh :: fresh == 0;
A.ObserveSwap(m, k, j);
    var m1 := K.Swap(m, k, j);
    A.ObserveSwap(m1, k, j);
    var m2 := K.Swap(m1, k, j);
    assert m1.Keys == m.Keys;
    assert k in m1 && j in m1;
    assert forall q :: q in m1 ==> q in m2 && m2[q] == (if q == k then m1[j] else if q == j then m1[k] else m1[q]);
    assert forall q :: q in m ==> q in m1 && m1[q] == (if q == k then m[j] else if q == j then m[k] else m[q]);
    assert forall q :: q in m ==> m2[q] == m[q];
    assert m2.Keys == m.Keys;
    A.Equal(m2, m);  }
}
