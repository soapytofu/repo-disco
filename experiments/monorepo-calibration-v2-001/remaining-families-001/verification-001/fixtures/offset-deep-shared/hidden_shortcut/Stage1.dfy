include "Kernel.dfy"
module Stage1 {
  export Public provides K, Split
  import K = Kernel`Internal
  lemma Split(s: seq<int>, t: seq<int>, o: int)
    requires |s| > 0
    ensures K.SplitReady(s,t,o)
  { reveal K.SplitReady(); }
}
