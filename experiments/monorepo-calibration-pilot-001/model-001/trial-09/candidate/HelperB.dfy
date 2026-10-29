include "Kernel.dfy"
include "HelperA.dfy"
module HelperB {
  import K = Kernel`Public
  import H = HelperA
  lemma {:induction false} Prove(s: seq<int>, t: seq<int>)
    ensures K.Total(s + t) == K.Total(s) + K.Total(t)
    decreases |s|
  {
    H.Prove(s, t);
  }
}
