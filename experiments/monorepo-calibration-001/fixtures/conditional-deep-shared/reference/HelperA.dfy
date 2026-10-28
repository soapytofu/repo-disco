include "Kernel.dfy"
include "Stage1.dfy"
include "Stage2.dfy"
include "Stage3.dfy"
module HelperA {
  import K = Kernel`Public
  import S1 = Stage1`Public
  import S2 = Stage2`Public
  import End = Stage3`Deep
  lemma {:induction false} Prove(x: int, y: int)
    ensures K.Safe(K.Encode(K.Abs(x), if y >= K.Abs(x) then y else K.Abs(x) + K.Abs(x) - y))
  {
    if x >= 0 {
      if y >= x {
        S1.Start(x, y);
        S2.Advance(x, y);
        End.Finish(x, y);
      } else {
        S1.Start(x, x + x - y);
        S2.Advance(x, x + x - y);
        End.Finish(x, x + x - y);
      }
    } else {
      if y >= -x {
        S1.Start(-x, y);
        S2.Advance(-x, y);
        End.Finish(-x, y);
      } else {
        S1.Start(-x, -x - x - y);
        S2.Advance(-x, -x - x - y);
        End.Finish(-x, -x - x - y);
      }
    }
  }
}
