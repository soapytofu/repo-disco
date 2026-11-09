include "Kernel.dfy"
module Ops1 {
  export Hidden provides K
  export Public provides K, SwapKeys
  import K = Kernel`Internal
  lemma SwapKeys(m: map<int,int>,k: int,j: int)
    requires k in m && j in m
    ensures K.Swap(m,k,j).Keys == m.Keys
  { reveal K.Swap(); }
}
