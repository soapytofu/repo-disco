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
  }
}
