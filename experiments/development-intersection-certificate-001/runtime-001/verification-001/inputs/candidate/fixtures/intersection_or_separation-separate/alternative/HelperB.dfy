include "Kernel.dfy"
include "Ops.dfy"
include "Api.dfy"
module HelperB {
  import K = Kernel`Public
  import O = Ops`Public
  import A = Api`Proof
  lemma {:induction false} Prove(a: int, b: int, c: int, d: int)
    requires a <= b && c <= d
    ensures K.Decided(a,b,c,d)
  {
    if a <= d && c <= b {
      var w := if b < d then b else d;
      O.Right(c,d,w);
      O.Left(a,b,w);
      A.Witness(a,b,c,d,w);
    } else if c > b {
      O.Before(b,c);
      A.Gap(a,b,c,d,-1);
    } else {
      O.After(d,a);
      A.Gap(a,b,c,d,1);
    }
  }
}
