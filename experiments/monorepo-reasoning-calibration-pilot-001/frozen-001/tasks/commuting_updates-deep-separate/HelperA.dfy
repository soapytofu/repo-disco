include "Kernel.dfy"
include "Ops1.dfy"
include "Ops2.dfy"
include "Api.dfy"
module HelperA {
  import K = Kernel`Public
  import O1 = Ops1`Public
  import O2 = Ops2`Public
  import A = Api`Deep
  lemma {:induction false} Prove(m: map<int,int>, k: int, j: int, x: int, y: int)
    requires k != j
    ensures K.Put(K.Put(m,k,x),j,y) == K.Put(K.Put(m,j,y),k,x)
  {
  }
}
