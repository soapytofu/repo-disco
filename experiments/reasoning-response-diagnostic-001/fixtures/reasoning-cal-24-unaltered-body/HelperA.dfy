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
    forall q | q in m[k := x][j := y].Keys ensures q in m[j := y][k := x].Keys && m[k := x][j := y][q] == m[j := y][k := x][q] {
      if q == j {
        assert m[k := x][j := y][q] == y;
        assert m[j := y][k := x][q] == y;
      } else {
        if q == k {
          assert m[k := x][j := y][q] == x;
          assert m[j := y][k := x][q] == x;
        } else {
          assert m[k := x][j := y][q] == m[q];
          assert m[j := y][k := x][q] == m[q];
        }
      }
    }
    forall q | q in m[j := y][k := x].Keys ensures q in m[k := x][j := y].Keys {
      assert q in m[k := x][j := y].Keys;
    }
    A.Equal(m[k := x][j := y], m[j := y][k := x]);  }
}
