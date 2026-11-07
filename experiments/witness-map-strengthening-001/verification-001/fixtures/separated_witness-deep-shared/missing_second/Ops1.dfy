include "Kernel.dfy"
module Ops1 {
  export Hidden provides K
  export Public provides K, Left, Right, Separate
  import K = Kernel`Internal
  lemma Left(a: int, b: int, w: int)
    requires a <= w <= b
    ensures K.LeftFact(a,b,w)
  { reveal K.LeftFact(); }
  lemma Right(c: int, d: int, w: int)
    requires c <= w <= d
    ensures K.RightFact(c,d,w)
  { reveal K.RightFact(); }
  lemma Separate(u: int, v: int, gap: int)
    requires 0 < gap && u + gap <= v
    ensures K.Separated(u,v,gap)
  { reveal K.Separated(); }
}
