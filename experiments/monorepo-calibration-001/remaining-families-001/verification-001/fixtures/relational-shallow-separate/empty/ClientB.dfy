include "Kernel.dfy"
include "HelperB.dfy"
module ClientB {
  import K = Kernel`Public
  import H = HelperB
  lemma Use(a: int, b: int, c: int)
    requires a >= 0 && b >= 0 && c >= a
    ensures K.Safe(a + b, c + b)
  { H.Prove(a + b, a + b, c + b); }
}
