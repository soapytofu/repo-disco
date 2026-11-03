include "Kernel.dfy"
include "Ops1.dfy"
include "Ops2.dfy"
include "Api.dfy"
module HelperA {
  import K = Kernel`Public
  import A = Api`Shallow
  lemma {:induction false} Prove(m: map<int,int>, k: int, j: int, v: int)
    ensures K.Drop(K.Put(m,k,v),j) == (if k == j then K.Drop(m,j) else K.Put(K.Drop(m,j),k,v))
  {
  }
}
