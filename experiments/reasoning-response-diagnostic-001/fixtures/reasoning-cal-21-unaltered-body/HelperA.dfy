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
    var putMKV := K.Put(m, k, v);
    A.ObserveDrop(putMKV, j);
    A.ObserveDrop(m, j);
    var dropMJ := K.Drop(m, j);
    if k == j {
      assert putMKV == m[k := v];
      assert K.Drop(putMKV, j) == (map q | q in putMKV && q != j :: putMKV[q]);
      assert K.Drop(m, j) == (map q | q in m && q != j :: m[q]);
      var lhs := K.Drop(putMKV, j);
      var rhs := K.Drop(m, j);
      assert lhs.Keys == rhs.Keys;
      forall q | q in lhs ensures q in rhs && lhs[q] == rhs[q] {
        assert q in m;
        assert q != j;
        assert lhs[q] == putMKV[q];
        assert q != k;
        assert putMKV[q] == m[q];
        assert rhs[q] == m[q];
      }
      A.Equal(lhs, rhs);
    } else {
      A.ObservePut(dropMJ, k, v);
      var lhs := K.Drop(putMKV, j);
      var rhs := K.Put(dropMJ, k, v);
      assert putMKV == m[k := v];
      assert lhs == (map q | q in putMKV && q != j :: putMKV[q]);
      assert dropMJ == (map q | q in m && q != j :: m[q]);
      assert rhs == dropMJ[k := v];
      assert lhs.Keys == rhs.Keys;
      forall q | q in lhs ensures q in rhs && lhs[q] == rhs[q] {
        if q == k {
          assert lhs[q] == putMKV[q];
          assert putMKV[q] == v;
          assert rhs[q] == v;
        } else {
          assert lhs[q] == putMKV[q];
          assert q in m;
          assert putMKV[q] == m[q];
          assert q in dropMJ;
          assert dropMJ[q] == m[q];
          assert rhs[q] == dropMJ[q];
        }
      }
      A.Equal(lhs, rhs);
    }  }
}
