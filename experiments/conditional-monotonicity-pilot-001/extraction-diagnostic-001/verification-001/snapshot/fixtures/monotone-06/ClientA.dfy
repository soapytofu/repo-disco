include "Kernel.dfy"
include "HelperA.dfy"
module ClientA {
  import K = Kernel`Public
  import H = HelperA
  lemma Target(x: int, y: int, l: int, h: int)
    requires x <= y && l <= h
    ensures K.Clamp(x,l,h) <= K.Clamp(y,l,h)
  { H.Prove(x,y,l,h); }
}
