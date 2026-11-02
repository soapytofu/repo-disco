include "Kernel.dfy"
include "HelperB.dfy"
module ClientB {
  import K = Kernel`Public
  import H = HelperB
  lemma Use(x: int, delta: int, l: int, h: int)
    requires delta >= 0 && l <= h
    ensures 0 <= K.Clamp((x-delta)+(delta),l,h) - K.Clamp(x-delta,l,h) <= delta
  { H.Prove(x-delta,delta,l,h); }
}
