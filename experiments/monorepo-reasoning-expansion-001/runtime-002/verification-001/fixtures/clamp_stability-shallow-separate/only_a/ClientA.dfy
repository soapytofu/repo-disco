include "Kernel.dfy"
include "HelperA.dfy"
module ClientA {
  import K = Kernel`Public
  import H = HelperA
  lemma Use(x: int, delta: int, l: int, h: int)
    requires delta >= 0 && l <= h
    ensures 0 <= K.Clamp((x)+(delta),l,h) - K.Clamp(x,l,h) <= delta
  { H.Prove(x,delta,l,h); }
}
