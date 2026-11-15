include "Kernel.dfy"
module Ops {
  export Public provides K, Left, Right, Before, After
  import K = Kernel`Internal
  lemma Left(a: int, b: int, w: int)
    requires a <= w <= b
    ensures K.LeftFact(a,b,w)
  { reveal K.LeftFact(); }
  lemma Right(c: int, d: int, w: int)
    requires c <= w <= d
    ensures K.RightFact(c,d,w)
  { reveal K.RightFact(); }
  lemma Before(b: int, c: int)
    requires b < c
    ensures K.LeftGap(b,c)
  { reveal K.LeftGap(); }
  lemma After(d: int, a: int)
    requires d < a
    ensures K.RightGap(d,a)
  { reveal K.RightGap(); }
}
