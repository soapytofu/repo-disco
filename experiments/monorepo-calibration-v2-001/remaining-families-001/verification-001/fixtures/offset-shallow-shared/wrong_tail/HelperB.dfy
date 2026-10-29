include "Kernel.dfy"
include "HelperA.dfy"
module HelperB {
  import K = Kernel`Public
  import H = HelperA
  lemma {:induction false} Prove(s: seq<int>, t: seq<int>, o: int)
    ensures K.Score(s+t,o) == K.Score(s,o) + K.Score(t,o+|s|)
    decreases |s|
  {
    H.Prove(s,t,o);
  }
}
