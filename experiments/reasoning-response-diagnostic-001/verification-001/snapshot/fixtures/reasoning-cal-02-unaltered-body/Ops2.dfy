include "Kernel.dfy"
module Ops2 {
  export Public provides K, Snoc
  import K = Kernel`Internal
  lemma Snoc(s: seq<int>, x: int)
    ensures K.Snoc(s,x) == s+[x]
  { reveal K.Snoc(); }
}
