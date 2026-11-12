include "Kernel.dfy"
module Ops1 {
  export Hidden provides K
  export Public provides K, Certify
  import K = Kernel`Internal
  lemma Certify(m: map<int,int>,a: int,b: int)
    requires a in m && b !in m && a != b
    ensures K.Ready(m,a,b)
  { reveal K.Ready(); }
}
