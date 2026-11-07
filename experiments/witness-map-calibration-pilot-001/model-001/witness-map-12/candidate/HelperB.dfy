include "Kernel.dfy"
include "Ops1.dfy"
include "Ops2.dfy"
include "Api.dfy"
module HelperB {
  import K = Kernel`Public
  import A = Api`Deep
  import O1 = Ops1`Public
  import O2 = Ops2`Public
  lemma {:induction false} Prove(a: int, b: int, c: int, d: int, gap: int)
    requires 0 < gap
    requires a + gap <= b && c + gap <= d && a + gap <= d && c + gap <= b
    ensures K.Room(a,b,c,d,gap)
  {O1.Left(a, b, a);
    O1.Right(c, d, a);
    O2.Join(a, b, c, d, a);
    O1.Left(a, b, a + gap);
    O1.Right(c, d, a + gap);
    O2.Join(a, b, c, d, a + gap);
    O1.Separate(a, a + gap, gap);
    A.Finish(a, b, c, d, gap, a, a + gap);  }
}
