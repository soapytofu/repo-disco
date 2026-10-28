include "Kernel.dfy"
include "Stage1.dfy"
include "Stage2.dfy"
include "Stage3.dfy"
module HelperB {
  import K = Kernel`Public
  import S1 = Stage1`Public
  import S2 = Stage2`Public
  import End = Stage3`Deep
  lemma {:induction false} Prove(x: int, y: int, z: int)
    requires 0 <= x <= y <= z
    ensures K.Safe(x, z)
  {
  }
}
