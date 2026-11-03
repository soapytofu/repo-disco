include "Kernel.dfy"
include "Ops1.dfy"
include "Ops2.dfy"
include "Api.dfy"
module HelperB {
  import K = Kernel`Public
  import O1 = Ops1`Public
  import O2 = Ops2`Public
  import A = Api`Deep
  lemma {:induction false} Prove(m: map<int,int>, k: int, j: int, x: int, y: int)
    requires k != j
    ensures K.Put(K.Put(m,k,x),j,y) == K.Put(K.Put(m,j,y),k,x)
  {O1.PutKeys(m, k, x);
    var m1 := K.Put(m, k, x);
    O1.PutKeys(m1, j, y);
    var lhs := K.Put(m1, j, y);
    O1.PutKeys(m, j, y);
    var m2 := K.Put(m, j, y);
    O1.PutKeys(m2, k, x);
    var rhs := K.Put(m2, k, x);
    assert lhs.Keys == m.Keys + {k} + {j};
    assert rhs.Keys == m.Keys + {j} + {k};
    assert lhs.Keys == rhs.Keys;
    forall q | q in lhs ensures q in rhs && lhs[q] == rhs[q] {
      O2.PutAt(m1, j, y, q);
      O2.PutAt(m2, k, x, q);
      if q == j {
        assert lhs[q] == y;
        assert rhs[q] == y;
      } else {
        if q == k {
          O2.PutAt(m, k, x, q);
          assert lhs[q] == x;
          assert rhs[q] == x;
        } else {
          O2.PutAt(m, k, x, q);
          O2.PutAt(m, j, y, q);
          assert lhs[q] == m[q];
          assert rhs[q] == m[q];
        }
      }
    }
    A.Equal(lhs, rhs);  }
}
