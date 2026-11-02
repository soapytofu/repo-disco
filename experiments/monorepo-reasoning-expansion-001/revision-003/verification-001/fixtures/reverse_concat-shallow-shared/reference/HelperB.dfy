include "Kernel.dfy"
include "HelperA.dfy"
module HelperB {
  import K = Kernel`Public
  import H = HelperA
  lemma {:induction false} Prove(s: seq<int>, t: seq<int>)
    ensures K.Rev(s+t) == K.Rev(t)+K.Rev(s)
    decreases |s|
  {
    H.Prove(s,t);
  }
}
