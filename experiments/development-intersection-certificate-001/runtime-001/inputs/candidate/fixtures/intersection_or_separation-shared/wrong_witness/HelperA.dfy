include "Kernel.dfy"
include "Ops.dfy"
include "Api.dfy"
module HelperA {
  import K = Kernel`Public
  import O = Ops`Public
  import A = Api`Proof
  lemma {:induction false} Prove(a: int, b: int, c: int, d: int)
    requires a <= b && c <= d
    ensures K.Decided(a,b,c,d)
  {
    if b < c {
      O.Before(b,c);
      A.Gap(a,b,c,d,-1);
    } else if d < a {
      O.After(d,a);
      A.Gap(a,b,c,d,1);
    } else {
      var w := a;
      O.Left(a,b,w);
      O.Right(c,d,w);
      A.Witness(a,b,c,d,w);
    }
  }
}
