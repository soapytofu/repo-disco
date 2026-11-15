include "HelperA.dfy"
module ClientA {
  import K = Kernel`Public
  import H = HelperA
  lemma {:induction false} Target(s: int, t: int, x: int)
    requires 0 <= s && 0 <= t
    ensures K.Cut(s,K.Cut(t,x)) == K.Cut(s+t,x)
  { H.Prove(s,t,x); }
}
