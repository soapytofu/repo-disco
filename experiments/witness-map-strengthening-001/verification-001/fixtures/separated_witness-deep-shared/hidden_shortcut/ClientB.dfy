include "Kernel.dfy"
include "HelperB.dfy"
module ClientB {
  import K = Kernel`Public
  import H = HelperB
  lemma Target(a: int, b: int, c: int, d: int, gap: int, shift: int)
    requires 0 < gap
    requires a + gap <= b && c + gap <= d && a + gap <= d && c + gap <= b
    ensures K.Room(c+shift,d+shift,a+shift,b+shift,gap)
  { H.Prove(c+shift,d+shift,a+shift,b+shift,gap); }
}
