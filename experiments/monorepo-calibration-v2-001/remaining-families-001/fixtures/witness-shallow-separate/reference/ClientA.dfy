include "Kernel.dfy"
include "HelperA.dfy"
module ClientA {
  import K = Kernel`Public
  import H = HelperA
  lemma Use(a: int, b: int, c: int, d: int)
    requires a <= b && c <= d && a <= d && c <= b
    ensures K.Overlap(a,b,c,d)
  { H.Prove(a,b,c,d); }
}
