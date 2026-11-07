include "Kernel.dfy"
include "Ops1.dfy"
include "Ops2.dfy"
include "Api.dfy"
module HelperA {
  import K = Kernel`Public
  import A = Api`Deep
  import O1 = Ops1`Public
  import O2 = Ops2`Public
  lemma {:induction false} Prove(m: map<int,int>, k: int, j: int, x: int, y: int)
    ensures K.Drop(K.Put(K.Put(m,k,x),j,y),k) == (if k == j then K.Drop(m,k) else K.Put(K.Drop(m,k),j,y))
  {var lhs := K.Drop(K.Put(K.Put(m,k,x),j,y),k);
    var inner := K.Put(m,k,x);
    var outer := K.Put(inner,j,y);
    O1.PutKeys(m,k,x);
    O1.PutKeys(inner,j,y);
    O1.DropKeys(outer,k);
    O1.DropKeys(m,k);
    if k == j {
      var rhs := K.Drop(m,k);
      assert lhs.Keys == rhs.Keys;
      forall q | q in lhs ensures q in rhs && lhs[q] == rhs[q] {
        O2.DropAt(outer,k,q);
        O2.DropAt(m,k,q);
        if q == j {
          O2.PutAt(inner,j,y,q);
          O2.PutAt(m,k,x,q);
        } else {
          O2.PutAt(inner,j,y,q);
          O2.PutAt(m,k,x,q);
        }
      }
      A.Equal(lhs, rhs);
    } else {
      var rhs := K.Put(K.Drop(m,k),j,y);
      var dm := K.Drop(m,k);
      O1.PutKeys(dm,j,y);
      assert lhs.Keys == rhs.Keys;
      forall q | q in lhs ensures q in rhs && lhs[q] == rhs[q] {
        O2.DropAt(outer,k,q);
        if q == j {
          O2.PutAt(inner,j,y,q);
          O2.PutAt(dm,j,y,q);
        } else {
          O2.PutAt(inner,j,y,q);
          O2.PutAt(dm,j,y,q);
          O2.DropAt(m,k,q);
          if q in m {
            O2.PutAt(m,k,x,q);
          }
        }
      }
      A.Equal(lhs, rhs);
    }  }
}
