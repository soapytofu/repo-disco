include "Kernel.dfy"
include "Ops1.dfy"
include "Ops2.dfy"
include "Api.dfy"
module HelperA {
  import K = Kernel`Public
  import A = Api`Shallow
  lemma {:induction false} Prove(m: map<int,int>, k: int, j: int, v: int)
    ensures true
  {
    var inserted := K.Put(m,k,v);
    var removed := K.Drop(m,j);
    var left := K.Drop(inserted,j);
    var right := if k == j then removed else K.Put(removed,k,v);
    A.ObservePut(m,k,v);
    A.ObserveDrop(inserted,j);
    A.ObserveDrop(m,j);
    A.ObservePut(removed,k,v);
    assert left.Keys == right.Keys;
    forall q | q in left
      ensures q in right && left[q] == right[q]
    {
    }
    A.Equal(left,right);
  }
}
