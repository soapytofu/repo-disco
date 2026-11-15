include "Kernel.dfy"
include "HelperA.dfy"
module ClientA {
  import K = Kernel`Public
  import H = HelperA
  lemma Target(c: int, a: int, b: int, d: int)
    requires 0 <= c && 0 <= a && 0 <= b && 0 <= d
    ensures K.Sat(c,K.Sat(c,a,b),d) == K.Sat(c,a,K.Sat(c,b,d))
  { H.Prove(c,a,b,d); }
}
