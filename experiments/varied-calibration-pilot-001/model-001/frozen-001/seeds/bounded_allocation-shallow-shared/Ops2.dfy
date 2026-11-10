include "Kernel.dfy"
module Ops2 {
  export Hidden provides K
  export Public provides K, Join
  import K = Kernel`Internal
  lemma Join(a: int,b: int,c: int,d: int,u: int,v: int)
    requires K.UBound(a,b,u) && K.VBound(c,d,v)
    ensures K.Bounds(a,b,c,d,u,v)
  { reveal K.Bounds(); }
}
