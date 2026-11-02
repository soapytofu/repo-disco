include "Kernel.dfy"
include "HelperB.dfy"
module ClientB {
  import K = Kernel`Public
  import H = HelperB
  lemma Use(x: int, l: int, h: int, a: int, b: int)
    requires l <= a <= b <= h
    ensures K.Clamp(K.Clamp(-x,-h,-l),-b,-a) == K.Clamp(-x,-b,-a)
  { H.Prove(-x,-h,-l,-b,-a); }
}
