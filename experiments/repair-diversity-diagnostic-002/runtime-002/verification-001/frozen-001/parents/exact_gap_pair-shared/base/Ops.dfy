include "Kernel.dfy"
module Ops {
  export Public provides K, Left, Right, Offset
  export Hidden provides K, HiddenBounds
  import K = Kernel`Internal
  lemma Left(a: int, b: int, u: int)
    requires a <= u <= b
    ensures K.Left(a,b,u)
  { reveal K.Left(); }
  lemma Right(c: int, d: int, v: int)
    requires c <= v <= d
    ensures K.Right(c,d,v)
  { reveal K.Right(); }
  lemma Offset(gap: int, u: int, v: int)
    requires 0 < gap && v == u + gap
    ensures K.Offset(gap,u,v)
  { reveal K.Offset(); }
  lemma HiddenBounds(a: int, b: int, u: int)
    requires a <= u <= b
    ensures K.Left(a,b,u)
  { Left(a,b,u); }
}
