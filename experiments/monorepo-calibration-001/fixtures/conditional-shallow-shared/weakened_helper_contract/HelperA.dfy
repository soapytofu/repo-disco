include "Kernel.dfy"
include "Stage1.dfy"
include "Stage2.dfy"
include "Stage3.dfy"
module HelperA {
  import K = Kernel`Public
  import End = Stage3`Shallow
  lemma {:induction false} Prove(x: int, y: int)
    ensures true
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
