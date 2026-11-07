include "Kernel.dfy"
include "Ops1.dfy"
include "Ops2.dfy"
include "Api.dfy"
module HelperA {
  import K = Kernel`Public
  import A = Api`Shallow
  import O1 = Ops1`Hidden
  import O2 = Ops2`Hidden
  lemma {:induction false} Prove(m: map<int,int>, k: int, j: int, x: int, y: int)
    ensures K.Drop(K.Put(K.Put(m,k,x),j,y),k) == (if k == j then K.Drop(m,k) else K.Put(K.Drop(m,k),j,y))
  {A.ObservePut(m, k, x);
    A.ObservePut(K.Put(m, k, x), j, y);
    A.ObserveDrop(K.Put(K.Put(m, k, x), j, y), k);
    A.ObserveDrop(m, k);
    if k == j {
      assert K.Drop(K.Put(K.Put(m, k, x), j, y), k) == K.Drop(m, k);
    } else {
      A.ObservePut(K.Drop(m, k), j, y);
      var lhs := K.Drop(K.Put(K.Put(m, k, x), j, y), k);
      var rhs := K.Put(K.Drop(m, k), j, y);
      assert lhs.Keys == rhs.Keys;
      forall q | q in lhs ensures q in rhs && lhs[q] == rhs[q] {
        assert q in rhs && lhs[q] == rhs[q];
      }
      A.Equal(lhs, rhs);
    }  }
}
