include "Kernel.dfy"
module Ops1 {
  export Public provides K, Unfold
  import K = Kernel`Internal
  lemma Unfold(s: seq<int>)
    requires |s| > 0
    ensures K.Rev(s) == K.Snoc(K.Rev(s[1..]),s[0])
  { reveal K.Rev(); }
}
