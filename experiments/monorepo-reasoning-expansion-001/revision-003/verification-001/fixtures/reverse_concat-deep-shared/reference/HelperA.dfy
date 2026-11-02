include "Kernel.dfy"
include "Ops1.dfy"
include "Ops2.dfy"
include "Api.dfy"
module HelperA {
  import K = Kernel`Public
  import O1 = Ops1`Public
  import O2 = Ops2`Public
  import A = Api`Deep
  lemma {:induction false} Prove(s: seq<int>, t: seq<int>)
    ensures K.Rev(s+t) == K.Rev(t)+K.Rev(s)
    decreases |s|
  {
    if |s| == 0 {
      A.Empty(s);
      assert s == [];
      assert s+t == t;
      assert K.Rev(s) == [];
      assert K.Rev(t)+K.Rev(s) == K.Rev(t);
      assert K.Rev(s+t) == K.Rev(t)+K.Rev(s);
    } else {
      Prove(s[1..],t);
      O1.Unfold(s+t);
      O2.Snoc(K.Rev((s+t)[1..]),(s+t)[0]);
      O1.Unfold(s);
      O2.Snoc(K.Rev((s)[1..]),(s)[0]);
      assert (s+t)[1..] == s[1..]+t;
      assert (s+t)[0] == s[0];
      assert K.Rev(s[1..]+t) == K.Rev(t)+K.Rev(s[1..]);
      assert K.Rev(s+t) == K.Rev(s[1..]+t)+[s[0]];
      assert K.Rev(s) == K.Rev(s[1..])+[s[0]];
      assert (K.Rev(t)+K.Rev(s[1..]))+[s[0]] == K.Rev(t)+(K.Rev(s[1..])+[s[0]]);
      assert K.Rev(s+t) == K.Rev(t)+K.Rev(s);
    }
    assert K.Rev(s+t) == K.Rev(t)+K.Rev(s);
  }
}
