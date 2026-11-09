include "Kernel.dfy"
module Ops1 {
  export Hidden provides K
  export Public provides K, Certify
  import K = Kernel`Internal
  lemma Certify(m: map<int,int>,k: int,j: int)
    requires k in m && j in m
    ensures K.Domain(m,k,j)
  { reveal K.Domain(); }
}
