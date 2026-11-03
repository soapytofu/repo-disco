include "Kernel.dfy"
include "Ops1.dfy"
include "Ops2.dfy"
include "Api.dfy"
module HelperA {
  import K = Kernel`Public
  import A = Api`Shallow
  lemma {:induction false} Prove(m: map<int,int>, k: int, j: int, x: int, y: int)
    requires k != j
    ensures K.Put(K.Put(m,k,x),j,y) == K.Put(K.Put(m,j,y),k,x)
  {A.ObservePut(m, k, x);
    var m1 := K.Put(m, k, x);
    A.ObservePut(m1, j, y);
    A.ObservePut(m, j, y);
    var m2 := K.Put(m, j, y);
    A.ObservePut(m2, k, x);
    var lhs := K.Put(K.Put(m, k, x), j, y);
    var rhs := K.Put(K.Put(m, j, y), k, x);
    forall q | q in lhs.Keys ensures q in rhs.Keys && lhs[q] == rhs[q] {
      assert q in rhs.Keys;
    }
    forall q | q in rhs.Keys ensures q in lhs.Keys {
      assert q in lhs.Keys;
    }
    A.Equal(lhs, rhs);  }
}
