include "Kernel.dfy"
include "Ops1.dfy"
include "Ops2.dfy"
include "Api.dfy"
module HelperA {
  import K = Kernel`Public
  import A = Api`Deep
  import O1 = Ops1`Public
  import O2 = Ops2`Public
  lemma {:induction false} Prove(m: map<int,int>, k: int, j: int, x: int, y: int)
    ensures K.Drop(K.Put(K.Put(m,k,x),j,y),k) == (if k == j then K.Drop(m,k) else K.Put(K.Drop(m,k),j,y))
  {
    if k == j {
    var u := K.Put(m,k,x);
    var v := K.Put(u,j,y);
    var left := K.Drop(v,k);
    var base := K.Drop(m,k);
    var right := if k == j then base else K.Put(base,j,y);
    O1.PutKeys(m,k,x); O1.PutKeys(u,j,y);
    O1.DropKeys(v,k); O1.DropKeys(m,k);
    if k != j { O1.PutKeys(base,j,y); }
    assert left.Keys == right.Keys;
    forall q | q in left ensures q in right && left[q] == right[q] {
      O2.DropAt(v,k,q); O2.PutAt(u,j,y,q);
      if k == j {
        O2.PutAt(m,k,x,q); O2.DropAt(m,k,q);
      } else {
        O2.PutAt(base,j,y,q);
        if q != j { O2.PutAt(m,k,x,q); O2.DropAt(m,k,q); }
      }
    }
    A.Equal(left,right);
    }
  }
}
