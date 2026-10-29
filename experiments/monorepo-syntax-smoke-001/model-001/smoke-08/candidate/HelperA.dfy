include "Kernel.dfy"
include "Stage1.dfy"
include "Stage2.dfy"
include "Stage3.dfy"
module HelperA {
  import K = Kernel`Public
  import S1 = Stage1`Public
  import S2 = Stage2`Public
  import End = Stage3`Deep
  lemma {:induction false} Prove(a: int, b: int, c: int, d: int)
    requires a <= b && c <= d && a <= d && c <= b
    ensures K.Overlap(a,b,c,d)
  {if a <= c {
  S1.Left(a, b, c);
  S1.Right(c, d, c);
  S2.Join(a, b, c, d, c);
  End.Finish(a, b, c, d, c);
} else {
  S1.Left(a, b, a);
  S1.Right(c, d, a);
  S2.Join(a, b, c, d, a);
  End.Finish(a, b, c, d, a);
}  }
}
