include "Kernel.dfy"
include "Ops1.dfy"
include "Ops2.dfy"
include "Api.dfy"
module HelperB {
  import K = Kernel`Public
  import A = Api`Shallow
  lemma {:induction false} Prove(m: map<int,int>, k: int, j: int, x: int, y: int)
    requires k != j
    ensures K.Put(K.Put(m,k,x),j,y) == K.Put(K.Put(m,j,y),k,x)
  {
    var u := K.Put(m,k,x);
    var v := K.Put(m,j,y);
    var left := K.Put(u,j,y);
    var right := K.Put(v,k,x);
    A.ObservePut(m,j,y);
    A.ObservePut(u,j,y);
    A.ObservePut(v,k,x);
    assert left.Keys == right.Keys;
    forall q | q in left
      ensures q in right && left[q] == right[q]
    {
    }
    A.Equal(left,right);
  }
}
