include "Kernel.dfy"
include "Ops.dfy"
module HelperA {
  import K = Kernel`Public
  import O = Ops`Public
  lemma {:induction false} Prove(c: int, a: int, b: int, d: int)
    requires 0 <= c && 0 <= a && 0 <= b && 0 <= d
    ensures K.Sat(c,K.Sat(c,a,b),d) == K.Sat(c,a,K.Sat(c,b,d))
  {
  }
}
