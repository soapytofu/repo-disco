include "HelperA.dfy"
module ClientA {
  import K = Kernel`Public
  import H = HelperA
  lemma {:induction false} Target(a: int, b: int, c: int, d: int, gap: int)
    requires 0 < gap && a <= b && c <= d && a + gap <= d && c <= b + gap
    ensures K.Feasible(a,b,c,d,gap)
  { H.Prove(a,b,c,d,gap); }
}
