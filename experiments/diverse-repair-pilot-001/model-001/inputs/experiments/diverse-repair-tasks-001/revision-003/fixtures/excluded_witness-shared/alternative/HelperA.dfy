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
      O.Bounds(a,b,a); assert a != e; A.Finish(a,b,e,a);
    } else {
      var v := a+1;
      O.Bounds(a,b,v); assert v != e; A.Finish(a,b,e,v);
    }
  }
}
