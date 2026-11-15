include "Kernel.dfy"
include "HelperB.dfy"
module ClientB {
  import K = Kernel`Public
  import H = HelperB
  lemma Target(c: int, a: int, b: int, d: int, e: int)
    requires 0 <= c && 0 <= a && 0 <= b && 0 <= d && 0 <= e
    ensures K.Sat(c,K.Sat(c,a+b,d),e) == K.Sat(c,a+b,K.Sat(c,d,e))
  { H.Prove(c,a+b,d,e); }
}
