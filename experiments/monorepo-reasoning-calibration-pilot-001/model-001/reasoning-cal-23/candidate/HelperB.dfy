include "Kernel.dfy"
include "Ops1.dfy"
include "Ops2.dfy"
include "Api.dfy"
module HelperB {
  import K = Kernel`Public
  import O1 = Ops1`Public
  import O2 = Ops2`Public
  import A = Api`Deep
  lemma {:induction false} Prove(s: seq<int>, t: seq<int>)
    ensures K.Rev(s+t) == K.Rev(t)+K.Rev(s)
    decreases |s|
  {if |s| == 0 {
  A.Empty(s);
  assert s + t == t;
  A.Empty(s);
} else {
  O1.Unfold(s + t);
  var head := s[0];
  var tail := s[1..];
  assert (s + t)[0] == head;
  assert (s + t)[1..] == tail + t;
  Prove(tail, t);
  O2.Snoc(K.Rev(t) + K.Rev(tail), head);
  O1.Unfold(s);
  O2.Snoc(K.Rev(tail), head);
  O2.Snoc(K.Rev(t) + K.Rev(tail), head);
  assert K.Snoc(K.Rev(t) + K.Rev(tail), head) == (K.Rev(t) + K.Rev(tail)) + [head];
  assert K.Snoc(K.Rev(tail), head) == K.Rev(tail) + [head];
  assert K.Rev(s) == K.Snoc(K.Rev(tail), head);
  assert K.Rev(s) == K.Rev(tail) + [head];
  assert K.Rev(t) + K.Rev(s) == K.Rev(t) + (K.Rev(tail) + [head]);
  assert (K.Rev(t) + K.Rev(tail)) + [head] == K.Rev(t) + (K.Rev(tail) + [head]);
}  }
}
