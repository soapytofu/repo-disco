include "HelperA.dfy"
module ClientA {
  import K = Kernel`Public
  import H = HelperA
  lemma {:induction false} Target(a: int, b: int, e: int)
    requires a < b
    ensures K.Feasible(a,b,e)
  { H.Prove(a,b,e); }
}
