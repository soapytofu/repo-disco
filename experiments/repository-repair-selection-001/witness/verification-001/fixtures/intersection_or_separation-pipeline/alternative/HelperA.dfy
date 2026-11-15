include "Kernel.dfy"
include "Ops.dfy"
module HelperA {
  import K = Kernel`Public
  import O = Ops`Membership
  lemma {:induction false} Prove(a: int, b: int, c: int, d: int)
    requires a <= b && c <= d && a <= d && c <= b
    ensures K.LeftFact(a,b,(if a < c then c else a))
    ensures K.RightFact(c,d,(if a < c then c else a))
  {
    if c > a {
      O.Right(c,d,c);
      O.Left(a,b,c);
    } else {
      O.Right(c,d,a);
      O.Left(a,b,a);
    }
  }
}
