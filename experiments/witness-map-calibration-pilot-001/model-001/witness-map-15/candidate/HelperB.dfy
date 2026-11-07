include "Kernel.dfy"
include "Ops1.dfy"
include "Ops2.dfy"
include "Api.dfy"
module HelperB {
  import K = Kernel`Public
  import A = Api`Shallow
  import O1 = Ops1`Hidden
  import O2 = Ops2`Hidden
  lemma {:induction false} Prove(m: map<int,int>, k: int, j: int, x: int, y: int)
    ensures K.Drop(K.Put(K.Put(m,k,x),j,y),k) == (if k == j then K.Drop(m,k) else K.Put(K.Drop(m,k),j,y))
  {A.ObservePut(m, k, x);
    A.ObservePut(m[k := x], j, y);
    A.ObserveDrop(m[k := x][j := y], k);
    A.ObserveDrop(m, k);
    A.ObservePut(K.Drop(m, k), j, y);
    if k == j {
      var lhs := (map q | q in m[k := x][j := y] && q != k :: m[k := x][j := y][q]);
      var rhs := (map q | q in m && q != k :: m[q]);
      assert lhs.Keys == rhs.Keys;
      forall q | q in lhs
        ensures q in rhs && lhs[q] == rhs[q]
      {
        assert q in rhs;
        assert lhs[q] == rhs[q];
      }
      A.Equal(lhs, rhs);
    } else {
      var lhs := (map q | q in m[k := x][j := y] && q != k :: m[k := x][j := y][q]);
      var dropM := (map q | q in m && q != k :: m[q]);
      var rhs := dropM[j := y];
      assert lhs.Keys == rhs.Keys;
      forall q | q in lhs
        ensures q in rhs && lhs[q] == rhs[q]
      {
        assert q in rhs;
        assert lhs[q] == rhs[q];
      }
      A.Equal(lhs, rhs);
    }  }
}
