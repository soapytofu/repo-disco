include "Kernel.dfy"
module Ops2 {
  export Public provides K, Select
  import K = Kernel`Internal
  lemma Select(x: int, p: int, tail: seq<int>)
    ensures K.Select(x,p,tail) == (if x <= p then [x]+tail else tail)
  { reveal K.Select(); }
}
