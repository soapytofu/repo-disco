include "HelperB.dfy"
module ClientB {
  import K = Kernel`Public
  import H = HelperB
  lemma {:induction false} Target(a: int, b: int, c: int, d: int, gap: int, shift: int)
    requires 0 < gap && a <= b && c <= d && a + gap <= d && c <= b + gap
    ensures K.Feasible(a+shift,b+shift,c+shift,d+shift,gap)
  { H.Prove(a+shift,b+shift,c+shift,d+shift,gap); }
}
