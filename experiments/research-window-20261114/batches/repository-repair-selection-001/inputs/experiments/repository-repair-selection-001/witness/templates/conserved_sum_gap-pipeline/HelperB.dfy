include "Kernel.dfy"
include "Ops.dfy"
include "Api.dfy"
include "HelperA.dfy"
module HelperB {
  import K = Kernel`Public
  import O = Ops`Gaps
  import A = Api`Proof
  import H = HelperA
  lemma {:induction false} Prove(a: int, b: int, c: int, d: int, s: int, g: int)
    requires a <= b && c <= d && a <= s - c && s - d <= b && 0 < g && a + a + g <= s && (s - d) + (s - d) + g <= s
    ensures K.Feasible(a,b,c,d,s,g)
  {
  }
}
