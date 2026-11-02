include "Kernel.dfy"
module Ops1 {
  export Public provides K, Unfold
  import K = Kernel`Internal
  lemma Unfold(s: seq<int>, p: int)
    requires |s| > 0
    ensures K.Filter(s,p) == K.Select(s[0],p,K.Filter(s[1..],p))
  { reveal K.Filter(); }
}
