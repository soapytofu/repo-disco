include "Kernel.dfy"
include "Ops.dfy"
include "Api.dfy"
module HelperA {
  import K = Kernel`Public
  import O = Ops`Public
  import A = Api`Public
  lemma {:induction false} Prove(a: int, b: int, c: int, d: int, gap: int)
    requires 0 < gap && a <= b && c <= d && a + gap <= d && c <= b + gap
    ensures K.Feasible(a,b,c,d,gap)
  {
  }
}
