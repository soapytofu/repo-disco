include "Kernel.dfy"
include "Ops1.dfy"
include "Ops2.dfy"
include "Api.dfy"
module HelperB {
  import K = Kernel`Public
  import O1 = Ops1`Public
  import O2 = Ops2`Public
  import A = Api`Deep
  lemma {:induction false} Prove(s: seq<int>, p: int, q: int)
    requires q <= p
    ensures K.Filter(K.Filter(s,p),q) == K.Filter(s,q)
    decreases |s|
  {
    if |s| == 0 {
      A.Empty(s,p); A.Empty(s,q); A.Empty([],q);
    } else {
      O1.Unfold(s,p);
      O2.Select((s)[0],p,K.Filter((s)[1..],p));
      O1.Unfold(s,q);
      O2.Select((s)[0],q,K.Filter((s)[1..],q));
      if s[0] <= p {
      O1.Unfold([s[0]]+K.Filter(s[1..],p),q);
      O2.Select(([s[0]]+K.Filter(s[1..],p))[0],q,K.Filter(([s[0]]+K.Filter(s[1..],p))[1..],q));
      }
    }
    assert K.Filter(K.Filter(s,p),q) == K.Filter(s,q);
  }
}
