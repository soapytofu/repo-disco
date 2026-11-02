include "Kernel.dfy"
include "HelperB.dfy"
module ClientB {
  import K = Kernel`Public
  import H = HelperB
  lemma Use(s: seq<int>, p: int, q: int, r: int)
    requires r <= q <= p
    ensures K.Filter(K.Filter(K.Filter(s,p),q),r) == K.Filter(s,r)
  { H.Prove(s,p,q); H.Prove(s,q,r); }
}
