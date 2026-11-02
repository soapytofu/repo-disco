include "Kernel.dfy"
module Api {
  export Shallow provides K, Empty, Observe
  export Deep provides K, Empty
  import K = Kernel`Internal
  lemma Empty(s: seq<int>)
    requires |s| == 0
    ensures K.Rev(s) == []
  { reveal K.Rev(); }
  lemma Observe(s: seq<int>)
    requires |s| > 0
    ensures K.Rev(s) == K.Rev(s[1..])+[s[0]]
  { reveal K.Rev(); reveal K.Snoc(); }
}
