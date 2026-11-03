include "Kernel.dfy"
include "Ops1.dfy"
include "Ops2.dfy"
include "Api.dfy"
module HelperA {
  import K = Kernel`Public
  import O1 = Ops1`Public
  import O2 = Ops2`Public
  import A = Api`Deep
  lemma {:induction false} Prove(s: seq<int>, p: int, q: int)
    requires q <= p
    ensures K.Filter(K.Filter(s,p),q) == K.Filter(s,q)
    decreases |s|
  {if |s| == 0 {
  A.Empty(s, p);
  A.Empty(s, q);
} else {
  O1.Unfold(s, p);
  O2.Select(s[0], p, K.Filter(s[1..], p));
  if s[0] <= p {
    var filtered_tail := K.Filter(s[1..], p);
    O1.Unfold([s[0]] + filtered_tail, q);
    O2.Select(s[0], q, K.Filter(filtered_tail, q));
    Prove(s[1..], p, q);
    O1.Unfold(s, q);
    O2.Select(s[0], q, K.Filter(s[1..], q));
    if s[0] <= q {
      assert K.Filter(K.Filter(s, p), q) == [s[0]] + K.Filter(filtered_tail, q);
      assert K.Filter(s, q) == [s[0]] + K.Filter(s[1..], q);
    } else {
      assert K.Filter(K.Filter(s, p), q) == K.Filter(filtered_tail, q);
      assert K.Filter(s, q) == K.Filter(s[1..], q);
    }
  } else {
    Prove(s[1..], p, q);
    O1.Unfold(s, q);
    O2.Select(s[0], q, K.Filter(s[1..], q));
    if s[0] <= q {
      assert false;
    } else {
      assert K.Filter(K.Filter(s, p), q) == K.Filter(K.Filter(s[1..], p), q);
      assert K.Filter(s, q) == K.Filter(s[1..], q);
    }
  }
}  }
}
