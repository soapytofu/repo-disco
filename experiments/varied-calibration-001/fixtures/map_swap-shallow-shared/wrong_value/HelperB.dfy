include "Kernel.dfy"
include "HelperA.dfy"
module HelperB {
  import K = Kernel`Public
  import H = HelperA
  lemma {:induction false} Prove(m: map<int,int>,k: int,j: int)
    requires k in m && j in m
    ensures K.Swap(K.Swap(m,k,j),k,j)==m
  {
    H.Prove(m,k,j);
  }
}
