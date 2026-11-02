include "Kernel.dfy"
include "HelperB.dfy"
module ClientB {
  import K = Kernel`Public
  import H = HelperB
  lemma Use(a: seq<int>, b: seq<int>, c: seq<int>, o: int)
    ensures K.Score((a+b)+c,o) == K.Score(a+b,o) + K.Score(c,o+|a+b|)
  { H.Prove(a+b,c,o); }
}
