include "Kernel.dfy"
include "HelperB.dfy"
module ClientB {
  import K = Kernel`Public
  import H = HelperB
  lemma Target(x: int, y: int, l: int, h: int)
    requires x <= y && l <= h
    ensures 0 <= K.Clamp(y,l,h) - K.Clamp(x,l,h)
  { H.Prove(x,y,l,h); }
}
