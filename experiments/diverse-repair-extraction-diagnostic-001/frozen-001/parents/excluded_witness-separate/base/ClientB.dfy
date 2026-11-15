include "HelperB.dfy"
module ClientB {
  import K = Kernel`Public
  import H = HelperB
  lemma {:induction false} Target(a: int, b: int, e: int)
    requires a < b
    ensures K.Feasible(a+1,b+1,e+1)
  { H.Prove(a+1,b+1,e+1); }
}
