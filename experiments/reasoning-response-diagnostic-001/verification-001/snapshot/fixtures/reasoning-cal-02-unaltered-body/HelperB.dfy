include "Kernel.dfy"
include "Ops1.dfy"
include "Ops2.dfy"
include "Api.dfy"
module HelperB {
  import K = Kernel`Public
  import A = Api`Shallow
  lemma {:induction false} Prove(s: seq<int>, t: seq<int>)
    ensures K.Rev(s+t) == K.Rev(t)+K.Rev(s)
    decreases |s|
  {if |s| == 0 {
  A.Empty(s);
  assert s + t == t;
  A.Empty(s);
} else {
  A.Observe(s);
  var s' := s[1..];
  assert s == [s[0]] + s';
  assert s + t == [s[0]] + (s' + t);
  Prove(s', t);
  A.Observe([s[0]] + (s' + t));
  assert K.Rev(s + t) == K.Rev(s' + t) + [s[0]];
  assert K.Rev(s' + t) == K.Rev(t) + K.Rev(s');
  assert K.Rev(s + t) == (K.Rev(t) + K.Rev(s')) + [s[0]];
  assert K.Rev(s) == K.Rev(s') + [s[0]];
  assert K.Rev(t) + K.Rev(s) == K.Rev(t) + (K.Rev(s') + [s[0]]);
  assert (K.Rev(t) + K.Rev(s')) + [s[0]] == K.Rev(t) + (K.Rev(s') + [s[0]]);
}  }
}
