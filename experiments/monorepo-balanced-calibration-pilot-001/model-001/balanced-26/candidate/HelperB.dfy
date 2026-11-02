include "Kernel.dfy"
include "Stage1.dfy"
include "Stage2.dfy"
include "Stage3.dfy"
module HelperB {
  import K = Kernel`Public
  import S1 = Stage1`Public
  import S2 = Stage2`Public
  import End = Stage3`Deep
  lemma {:induction false} Prove(x: int, y: int)
    ensures K.Safe(K.Encode(K.Abs(x), if y >= K.Abs(x) then y else K.Abs(x) + K.Abs(x) - y))
  {if y >= K.Abs(x) {
  S1.Start(K.Abs(x), y);
  S2.Advance(K.Abs(x), y);
  End.Finish(K.Abs(x), y);
} else {
  S1.Start(K.Abs(x), K.Abs(x) + K.Abs(x) - y);
  S2.Advance(K.Abs(x), K.Abs(x) + K.Abs(x) - y);
  End.Finish(K.Abs(x), K.Abs(x) + K.Abs(x) - y);
}  }
}
