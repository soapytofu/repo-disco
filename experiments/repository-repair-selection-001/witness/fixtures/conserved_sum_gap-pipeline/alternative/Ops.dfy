include "Kernel.dfy"
module Ops {
  export Bounds provides K, Left, Right, Sum
  export Gaps provides K, Gap
  import K = Kernel`Internal
  lemma Left(a: int, b: int, u: int)
    requires a <= u <= b
    ensures K.LeftFact(a,b,u)
  { reveal K.LeftFact(); }
  lemma Right(c: int, d: int, v: int)
    requires c <= v <= d
    ensures K.RightFact(c,d,v)
  { reveal K.RightFact(); }
  lemma Sum(s: int, u: int, v: int)
    requires u + v == s
    ensures K.SumFact(s,u,v)
  { reveal K.SumFact(); }
  lemma Gap(g: int, u: int, v: int)
    requires 0 < g && u + g <= v
    ensures K.GapFact(g,u,v)
  { reveal K.GapFact(); }
}
