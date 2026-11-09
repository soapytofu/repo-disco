include "Kernel.dfy"
include "Ops1.dfy"
include "Ops2.dfy"
include "Api.dfy"
module HelperA {
  import K = Kernel`Public
  import A = Api`Shallow
  import O1 = Ops1`Hidden
  import O2 = Ops2`Hidden
  lemma {:induction false} Prove(m: map<int,int>,k: int,j: int)
    requires k in m && j in m
    ensures K.Swap(K.Swap(m,k,j),k,j)==m
  {
  }
}
