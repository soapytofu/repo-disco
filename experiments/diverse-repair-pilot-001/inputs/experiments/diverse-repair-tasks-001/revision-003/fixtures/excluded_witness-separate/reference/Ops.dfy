include "Kernel.dfy"
module Ops {
  export Public provides K, Bounds
  import K = Kernel`Internal
  lemma Bounds(a: int, b: int, u: int)
    requires a <= u <= b
    ensures K.InRange(a,b,u)
  { reveal K.InRange(); }
}
