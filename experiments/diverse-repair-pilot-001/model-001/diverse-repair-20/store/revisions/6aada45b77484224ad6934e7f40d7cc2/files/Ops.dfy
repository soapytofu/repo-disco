include "Kernel.dfy"
module Ops {
  export Public provides K, Unfold
  import K = Kernel`Internal
  lemma Unfold(s: seq<int>, t: seq<int>)
    requires |s| > 0 && |t| > 0
    ensures K.Weave(s,t) == [s[0],t[0]] + K.Weave(s[1..],t[1..])
  { reveal K.Weave(); }
}
