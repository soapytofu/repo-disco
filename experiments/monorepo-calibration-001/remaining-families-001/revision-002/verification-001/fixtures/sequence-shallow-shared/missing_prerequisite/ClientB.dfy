include "Kernel.dfy"
include "HelperB.dfy"
module ClientB {
  import K = Kernel`Public
  import H = HelperB
  lemma Use(a: seq<int>, b: seq<int>, c: seq<int>)
    ensures K.Total((a + b) + c) == K.Total(a + b) + K.Total(c)
  { H.Prove(a + b, c); }
}
