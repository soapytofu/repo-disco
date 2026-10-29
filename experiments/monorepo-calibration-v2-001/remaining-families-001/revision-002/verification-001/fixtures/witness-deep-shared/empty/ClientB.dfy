include "Kernel.dfy"
include "HelperB.dfy"
module ClientB {
  import K = Kernel`Public
  import H = HelperB
  lemma Use(a: int, b: int, c: int, d: int, shift: int)
    requires a <= b && c <= d && a <= d && c <= b
    ensures K.Overlap(c+shift,d+shift,a+shift,b+shift)
  { H.Prove(c+shift,d+shift,a+shift,b+shift); }
}
