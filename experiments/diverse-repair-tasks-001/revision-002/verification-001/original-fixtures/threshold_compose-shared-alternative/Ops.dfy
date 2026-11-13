include "Kernel.dfy"
module Ops {
  export Public provides K, Below, Above
  import K = Kernel`Internal
  lemma Below(t: int, x: int)
    requires x <= t
    ensures K.Cut(t,x) == 0
  { reveal K.Cut(); }
  lemma Above(t: int, x: int)
    requires t < x
    ensures K.Cut(t,x) == x-t
  { reveal K.Cut(); }
}
