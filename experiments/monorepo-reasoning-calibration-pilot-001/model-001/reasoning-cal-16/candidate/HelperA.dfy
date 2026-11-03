include "Kernel.dfy"
include "Ops1.dfy"
include "Ops2.dfy"
include "Api.dfy"
module HelperA {
  import K = Kernel`Public
  import O1 = Ops1`Public
  import O2 = Ops2`Public
  import A = Api`Deep
  lemma {:induction false} Prove(m: map<int,int>, k: int, j: int, v: int)
    ensures K.Drop(K.Put(m,k,v),j) == (if k == j then K.Drop(m,j) else K.Put(K.Drop(m,j),k,v))
  {O1.PutKeys(m, k, v);
    var putMKV := K.Put(m, k, v);
    O1.DropKeys(putMKV, j);
    O1.DropKeys(m, j);
    var dropMJ := K.Drop(m, j);
    var lhs := K.Drop(putMKV, j);
    if k == j {
      assert lhs.Keys == dropMJ.Keys;
      forall q | q in lhs ensures q in dropMJ && lhs[q] == dropMJ[q] {
        O2.DropAt(putMKV, j, q);
        O2.PutAt(m, k, v, q);
        O2.DropAt(m, j, q);
      }
      A.Equal(lhs, dropMJ);
    } else {
      O1.PutKeys(dropMJ, k, v);
      var rhs := K.Put(dropMJ, k, v);
      assert lhs.Keys == rhs.Keys;
      forall q | q in lhs ensures q in rhs && lhs[q] == rhs[q] {
        O2.DropAt(putMKV, j, q);
        O2.PutAt(m, k, v, q);
        if q == k {
          O2.PutAt(dropMJ, k, v, q);
        } else {
          O2.DropAt(m, j, q);
          O2.PutAt(dropMJ, k, v, q);
        }
      }
      A.Equal(lhs, rhs);
    }  }
}
