include "Kernel.dfy"
include "Stage1.dfy"
include "Stage2.dfy"
include "Stage3.dfy"
module HelperA {
  import K = Kernel`Public
  import End = Stage3`Shallow
  lemma {:induction false} Prove(x: int, y: int, z: int)
    requires 0 <= x <= y <= z
    ensures K.Safe(x, z)
  {
    End.Direct(x, z, y);
  }
}
