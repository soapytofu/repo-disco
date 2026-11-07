include "Kernel.dfy"
include "Ops1.dfy"
include "Ops2.dfy"
include "Api.dfy"
module HelperA {
  import K = Kernel`Public
  import A = Api`Deep
  import O1 = Ops1`Public
  import O2 = Ops2`Public
  lemma {:induction false} Prove(a: int, b: int, c: int, d: int, gap: int)
    requires 0 < gap
    requires a + gap <= b && c + gap <= d && a + gap <= d && c + gap <= b
    ensures K.Room(a,b,c,d,gap)
  {if c <= a {
  O1.Left(a, b, a);
  O1.Right(c, d, a);
  O2.Join(a, b, c, d, a);
  O1.Left(a, b, a + gap);
  O1.Right(c, d, a + gap);
  O2.Join(a, b, c, d, a + gap);
  O1.Separate(a, a + gap, gap);
  A.Finish(a, b, c, d, gap, a, a + gap);
} else {
  O1.Left(a, b, c);
  O1.Right(c, d, c);
  O2.Join(a, b, c, d, c);
  O1.Left(a, b, c + gap);
  O1.Right(c, d, c + gap);
  O2.Join(a, b, c, d, c + gap);
  O1.Separate(c, c + gap, gap);
  A.Finish(a, b, c, d, gap, c, c + gap);
}  }
}
