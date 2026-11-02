include "Kernel.dfy"
include "Ops1.dfy"
include "Ops2.dfy"
include "Api.dfy"
module HelperA {
  import K = Kernel`Public
  import O1 = Ops1`Public
  import O2 = Ops2`Public
  import A = Api`Deep
  lemma {:induction false} Prove(m: map<int,int>, k: int, j: int, x: int, y: int)
    requires k != j
    ensures K.Put(K.Put(m,k,x),j,y) == K.Put(K.Put(m,j,y),k,x)
  {
    var u := K.Put(m,k,x);
    var v := K.Put(m,j,y);
    var left := K.Put(u,j,y);
    var right := K.Put(v,k,x);
    O1.PutKeys(m,k,x);
    O1.PutKeys(m,j,y);
    O1.PutKeys(u,j,y);
    O1.PutKeys(v,k,x);
    assert left.Keys == right.Keys;
    forall q | q in left
      ensures q in right && left[q] == right[q]
    {
      O2.PutAt(u,j,y,q); O2.PutAt(v,k,x,q);
      if q != j { O2.PutAt(m,k,x,q); }
      if q != k { O2.PutAt(m,j,y,q); }
    }
    A.Equal(left,right);
  }
}
