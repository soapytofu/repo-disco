include "Kernel.dfy"
include "Ops.dfy"
include "Api.dfy"
module HelperA {
  import K = Kernel`Public
  import O = Ops`Public
  import A = Api`Public
  lemma {:induction false} Prove(a: int, b: int, e: int)
    requires a < b
    ensures K.Feasible(a,b,e)
  {
    if a != e {
      var u := a;
      O.Bounds(a, b, u);
      A.Finish(a, b, e, u);
    } else {
      var u := b;
      O.Bounds(a, b, u);
      A.Finish(a, b, e, u);
    }
    }
}
