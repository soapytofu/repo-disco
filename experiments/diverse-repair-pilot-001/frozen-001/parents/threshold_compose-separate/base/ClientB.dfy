include "HelperB.dfy"
module ClientB {
  import K = Kernel`Public
  import H = HelperB
  lemma {:induction false} Target(s: int, t: int, x: int)
    requires 0 <= s && 0 <= t
    ensures K.Cut(t,K.Cut(s,x)) == K.Cut(t+s,x)
  { H.Prove(t,s,x); }
}
