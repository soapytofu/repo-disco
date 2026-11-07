include "Kernel.dfy"
include "Ops1.dfy"
include "Ops2.dfy"
include "Api.dfy"
module HelperB {
  import K = Kernel`Public
  import A = Api`Deep
  import O1 = Ops1`Public
  import O2 = Ops2`Public
  lemma {:induction false} Prove(m: map<int,int>, k: int, j: int, x: int, y: int)
    ensures K.Drop(K.Put(K.Put(m,k,x),j,y),k) == (if k == j then K.Drop(m,k) else K.Put(K.Drop(m,k),j,y))
  {    var u := K.Put(m,k,x);
    var v := K.Put(u,j,y);
    var base := K.Drop(m,k);
    var left := K.Drop(v,k);
    var right := if k == j then base else K.Put(base,j,y);
    O1.DropKeys(m,k); O1.PutKeys(m,k,x);
    O1.PutKeys(u,j,y); O1.DropKeys(v,k);
    if j != k { O1.PutKeys(base,j,y); }
    assert left.Keys == right.Keys;
    forall q | q in left ensures q in right && left[q] == right[q] {
      O2.DropAt(v,k,q); O2.PutAt(u,j,y,q);
      if q == j {
        assert j != k;
        O2.PutAt(base,j,y,q);
      } else {
        O2.PutAt(m,k,x,q); O2.DropAt(m,k,q);
        if j != k { O2.PutAt(base,j,y,q); }
      }
    }
    A.Equal(left,right);
  }
}
