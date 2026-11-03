include "Kernel.dfy"
include "Ops1.dfy"
include "Ops2.dfy"
include "Api.dfy"
module HelperA {
  import K = Kernel`Public
  import A = Api`Shallow
  lemma {:induction false} Prove(m: map<int,int>, k: int, j: int, v: int)
    ensures K.Drop(K.Put(m,k,v),j) == (if k == j then K.Drop(m,j) else K.Put(K.Drop(m,j),k,v))
  {A.ObservePut(m, k, v);
    A.ObserveDrop(K.Put(m, k, v), j);
    A.ObserveDrop(m, j);
    if k == j {
      assert K.Drop(K.Put(m, k, v), j) == K.Drop(m, j);
    } else {
      A.ObservePut(K.Drop(m, j), k, v);
      var lhs := K.Drop(K.Put(m, k, v), j);
      var rhs := K.Put(K.Drop(m, j), k, v);
      assert lhs.Keys == rhs.Keys;
      forall q | q in lhs ensures q in rhs && lhs[q] == rhs[q] {
        assert q in rhs;
        assert lhs[q] == rhs[q];
      }
      A.Equal(lhs, rhs);
    }  }
}
