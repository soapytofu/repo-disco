include "Kernel.dfy"
include "HelperA.dfy"
module HelperB {
  import K = Kernel`Public
  import H = HelperA
  lemma {:induction false} Prove(x: int, y: int)
    ensures K.Safe(K.Encode(K.Abs(x), if y >= K.Abs(x) then y else K.Abs(x) + K.Abs(x) - y))
  {
    H.Prove(x, y);
  }
}
