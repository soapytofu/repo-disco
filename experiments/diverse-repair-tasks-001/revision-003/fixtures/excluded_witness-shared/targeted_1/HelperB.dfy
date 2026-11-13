include "HelperA.dfy"
module HelperB {
  import K = Kernel`Public
  import H = HelperA
  lemma {:induction false} Prove(a: int, b: int, e: int)
    requires a < b
    ensures K.Feasible(a,b,e)
  { H.Prove(a,b,e); }
}
