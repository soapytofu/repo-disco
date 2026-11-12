include "Kernel.dfy"
module Ops1 {
  export Hidden provides K
  export Public provides K, Certify
  import K = Kernel`Internal
  lemma Certify(m: map<int,int>,n: map<int,int>)
    requires forall q :: q in m ==> q !in n
    ensures K.Separate(m,n)
  { reveal K.Separate(); }
}
