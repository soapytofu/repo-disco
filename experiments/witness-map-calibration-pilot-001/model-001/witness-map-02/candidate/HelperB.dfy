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
  {var m1 := K.Put(m, k, x);
    var m2 := K.Put(m1, j, y);
    var lhs := K.Drop(m2, k);
    O1.PutKeys(m, k, x);
    O1.PutKeys(m1, j, y);
    O1.DropKeys(m2, k);
    O1.DropKeys(m, k);
    var dm := K.Drop(m, k);
    if k == j {
      assert lhs.Keys == dm.Keys;
      forall q | q in lhs
        ensures q in dm && lhs[q] == dm[q]
      {
        O2.DropAt(m2, k, q);
        O2.PutAt(m1, j, y, q);
        O2.PutAt(m, k, x, q);
        O2.DropAt(m, k, q);
      }
      A.Equal(lhs, dm);
    } else {
      var rhs := K.Put(dm, j, y);
      O1.PutKeys(dm, j, y);
      assert lhs.Keys == rhs.Keys;
      forall q | q in lhs
        ensures q in rhs && lhs[q] == rhs[q]
      {
        O2.DropAt(m2, k, q);
        O2.PutAt(m1, j, y, q);
        if q == j {
          O2.PutAt(dm, j, y, q);
        } else {
          O2.PutAt(m, k, x, q);
          O2.DropAt(m, k, q);
          O2.PutAt(dm, j, y, q);
        }
      }
      A.Equal(lhs, rhs);
    }  }
}
