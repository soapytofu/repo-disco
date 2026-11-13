include "Kernel.dfy"
include "Ops.dfy"
include "Api.dfy"
module HelperB {
  import K = Kernel`Public
  import O = Ops`Public
  import A = Api`Public
  lemma {:induction false} Prove(a: int, b: int, e: int)
    requires a < b
    ensures K.Feasible(a,b,e)
  {
    var u := if a == e then a+1 else a;
    assert u != e;
    A.Finish(a,b,e,u);
  }
}
