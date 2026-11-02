include "Kernel.dfy"
include "Ops1.dfy"
include "Ops2.dfy"
include "Api.dfy"
module HelperA {
  import K = Kernel`Public
  import O1 = Ops1`Public
  import O2 = Ops2`Public
  import A = Api`Deep
  lemma {:induction false} Prove(m: map<int,int>, k: int, j: int, v: int)
    ensures K.Drop(K.Put(m,k,v),j) == (if k == j then K.Drop(m,j) else K.Put(K.Drop(m,j),k,v))
  {
    var inserted := K.Put(m,k,v);
    var removed := K.Drop(m,j);
    var left := K.Drop(inserted,j);
    var right := if k == j then removed else K.Put(removed,k,v);
    O1.PutKeys(m,k,v);
    O1.DropKeys(inserted,j);
    O1.DropKeys(m,j);
    O1.PutKeys(removed,k,v);
    assert left.Keys == right.Keys;
    forall q | q in left
      ensures q in right && left[q] == right[q]
    {
      O2.DropAt(inserted,j,q);
      O2.PutAt(m,k,v,q);
      if k == j {
        O2.DropAt(m,j,q);
      } else {
        O2.PutAt(removed,k,v,q);
        if q != k { O2.DropAt(m,j,q); }
      }
    }
    A.Equal(left,right);
    assert left == K.Put(m,k,v);
  }
}
