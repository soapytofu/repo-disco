include "Kernel.dfy"
include "Ops1.dfy"
include "Ops2.dfy"
include "Api.dfy"
module HelperB {
  import K = Kernel`Public
  import A = Api`Shallow
  lemma {:induction false} Prove(s: seq<int>, p: int, q: int)
    requires q <= p
    ensures K.Filter(K.Filter(s,p),q) == K.Filter(s,q)
    decreases |s|
  {
    if |s| == 0 {
      A.Empty(s,p); A.Empty(s,q); A.Empty([],q);
    } else {
      Prove(s[1..],p,q);
      A.Observe(s,p);
      A.Observe(s,q);
      if s[0] <= p {
      A.Observe([s[0]]+K.Filter(s[1..],p),q);
      }
    }
    assert K.Filter(K.Filter(s,p),q) == K.Filter(s,q);
  }
}
