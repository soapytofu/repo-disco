include "Kernel.dfy"
include "Ops.dfy"
include "Api.dfy"
include "HelperA.dfy"
module HelperB {
  import K = Kernel`Public
  import O = Ops`Gaps
  import A = Api`Proof
  import H = HelperA
  lemma {:induction false} Prove(a: int, b: int, c: int, d: int)
    requires a <= b && c <= d
    ensures K.Decided(a,b,c,d)
  {
    if b < c {
      O.Before(b,c);
      A.Gap(a,b,c,d,1);
    } else if d < a {
      O.After(d,a);
      A.Gap(a,b,c,d,1);
    } else {
      H.Prove(a,b,c,d);
      var w := if a < c then c else a;
      A.Witness(a,b,c,d,w);
    }
  }
}
