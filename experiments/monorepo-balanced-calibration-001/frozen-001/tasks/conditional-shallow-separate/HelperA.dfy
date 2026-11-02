include "Kernel.dfy"
include "Stage1.dfy"
include "Stage2.dfy"
include "Stage3.dfy"
module HelperA {
  import K = Kernel`Public
  import End = Stage3`Shallow
  lemma {:induction false} Prove(x: int, y: int)
    ensures K.Safe(K.Encode(K.Abs(x), if y >= K.Abs(x) then y else K.Abs(x) + K.Abs(x) - y))
  {
  }
}
