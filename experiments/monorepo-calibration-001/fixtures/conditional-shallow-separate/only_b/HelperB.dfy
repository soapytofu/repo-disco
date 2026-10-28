include "Kernel.dfy"
include "Stage1.dfy"
include "Stage2.dfy"
include "Stage3.dfy"
module HelperB {
  import K = Kernel`Public
  import End = Stage3`Shallow
  lemma {:induction false} Prove(x: int, y: int)
    ensures K.Safe(K.Encode(K.Abs(x), if y >= K.Abs(x) then y else K.Abs(x) + K.Abs(x) - y))
  {
    if x >= 0 {
      if y >= x {
        End.Direct(x, y);
      } else {
        End.Direct(x, x + x - y);
      }
    } else {
      if y >= -x {
        End.Direct(-x, y);
      } else {
        End.Direct(-x, -x - x - y);
      }
    }
  }
}
