include "Kernel.dfy"
include "HelperA.dfy"
module ClientA {
  import K = Kernel`Public
  import H = HelperA
  lemma Use(s: seq<int>, t: seq<int>, o: int)
    ensures K.Score(s+t,o) == K.Score(s,o) + K.Score(t,o+|s|)
  { H.Prove(s,t,o); }
}
