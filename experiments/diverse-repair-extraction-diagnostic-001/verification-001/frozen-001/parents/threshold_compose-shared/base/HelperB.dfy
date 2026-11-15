include "HelperA.dfy"
module HelperB {
  import K = Kernel`Public
  import H = HelperA
  lemma {:induction false} Prove(s: int, t: int, x: int)
    requires 0 <= s && 0 <= t
    ensures K.Cut(s,K.Cut(t,x)) == K.Cut(s+t,x)
  { H.Prove(s,t,x); }
}
