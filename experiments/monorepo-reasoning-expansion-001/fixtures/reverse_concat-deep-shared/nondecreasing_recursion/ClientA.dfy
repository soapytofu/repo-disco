include "Kernel.dfy"
include "HelperA.dfy"
module ClientA {
  import K = Kernel`Public
  import H = HelperA
  lemma Use(s: seq<int>, t: seq<int>)
    ensures K.Rev(s+t) == K.Rev(t)+K.Rev(s)
  { H.Prove(s,t); }
}
