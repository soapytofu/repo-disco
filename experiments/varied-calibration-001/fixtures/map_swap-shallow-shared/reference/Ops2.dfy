include "Kernel.dfy"
module Ops2 {
  export Hidden provides K
  export Public provides K, SwapAt
  import K = Kernel`Internal
  lemma SwapAt(m: map<int,int>,k: int,j: int,q: int)
    requires k in m && j in m && q in m
    ensures q in K.Swap(m,k,j)
    ensures K.Swap(m,k,j)[q] == (if q==k then m[j] else if q==j then m[k] else m[q])
  { reveal K.Swap(); if k==j { assert m[k]==m[j]; } }
}
