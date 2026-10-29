include "Kernel.dfy"
include "Stage1.dfy"
include "Stage2.dfy"
include "Stage3.dfy"
module HelperB {
  import K = Kernel`Public
  import End = Stage3`Shallow
  lemma {:induction false} Prove(a: int, b: int, c: int, d: int)
    requires a <= b && c <= d && a <= d && c <= b
    ensures K.Overlap(a,b,c,d)
  {
    if a < c {
      End.Direct(a,b,c,d,a);
    } else {
      End.Direct(a,b,c,d,c);
    }
  }
}
