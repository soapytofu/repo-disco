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
  {
    var u := K.Put(m,k,x);
    var v := K.Put(u,j,y);
    var left := K.Drop(v,k);
    var base := K.Drop(m,k);
    var right := if k == j then base else K.Put(base,j,y);
    A.ObservePut(m,k,x); A.ObservePut(u,j,y);
    A.ObserveDrop(v,k); A.ObserveDrop(m,k);
    if k != j { A.ObservePut(base,j,y); }
    assert left.Keys == right.Keys;
    forall q | q in left ensures q in right && left[q] == right[q] {
    }
    A.Equal(left,right);
  }
}
