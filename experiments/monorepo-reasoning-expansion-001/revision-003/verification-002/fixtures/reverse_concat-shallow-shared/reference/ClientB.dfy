include "Kernel.dfy"
include "HelperB.dfy"
module ClientB {
  import K = Kernel`Public
  import H = HelperB
  lemma Use(a: seq<int>, b: seq<int>, c: seq<int>)
    ensures K.Rev((a+b)+c) == K.Rev(c)+(K.Rev(b)+K.Rev(a))
  { H.Prove(a+b,c); H.Prove(a,b); }
}
