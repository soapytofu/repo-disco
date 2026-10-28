include "Kernel.dfy"
include "HelperA.dfy"
module ClientA {
  import K = Kernel`Public
  import H = HelperA
  lemma Use(s: seq<int>, t: seq<int>)
    ensures K.Total(s + t) == K.Total(s) + K.Total(t)
  { H.Prove(s, t); }
}
