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
  {var lhs := K.Put(K.Put(m,k,x),j,y);
    var rhs := K.Put(K.Put(m,j,y),k,x);
    A.ObservePut(m,k,x);
    A.ObservePut(m,j,y);
    var mk := m[k := x];
    var mj := m[j := y];
    A.ObservePut(mk,j,y);
    A.ObservePut(mj,k,x);
    assert lhs == mk[j := y];
    assert rhs == mj[k := x];
    assert mk[j := y] == m[k := x][j := y];
    assert mj[k := x] == m[j := y][k := x];
    forall q | q in lhs.Keys ensures q in rhs.Keys && lhs[q] == rhs[q] {
      if q == j {
        assert lhs[q] == y;
        assert rhs[q] == y;
      } else {
        if q == k {
          assert lhs[q] == x;
          assert rhs[q] == x;
        } else {
          assert lhs[q] == m[q];
          assert rhs[q] == m[q];
        }
      }
    }
    forall q | q in rhs.Keys ensures q in lhs.Keys {
      assert q in lhs.Keys;
    }
    A.Equal(lhs, rhs);  }
}
