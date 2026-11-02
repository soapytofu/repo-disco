include "Kernel.dfy"
module Api {
  export Shallow provides K, Empty, Observe
  export Deep provides K, Empty
  import K = Kernel`Internal
  lemma Empty(s: seq<int>, p: int)
    requires |s| == 0
    ensures K.Filter(s,p) == []
  { reveal K.Filter(); }
  lemma Observe(s: seq<int>, p: int)
    requires |s| > 0
    ensures K.Filter(s,p) == (if s[0] <= p then [s[0]]+K.Filter(s[1..],p) else K.Filter(s[1..],p))
  { reveal K.Filter(); reveal K.Select(); }
}
