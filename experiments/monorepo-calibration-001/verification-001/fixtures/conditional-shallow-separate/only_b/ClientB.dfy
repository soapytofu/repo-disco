include "Kernel.dfy"
include "HelperB.dfy"
module ClientB {
  import K = Kernel`Public
  import H = HelperB
  lemma Use(a: int, b: int)
    ensures K.Safe(K.Encode(K.Abs(a - b), if (a + b) >= K.Abs(a - b) then (a + b) else K.Abs(a - b) + K.Abs(a - b) - (a + b)))
  { H.Prove(a - b, a + b); }
}
