include "Kernel.dfy"
include "Ops1.dfy"
include "Ops2.dfy"
include "Api.dfy"
module HelperA {
  import K = Kernel`Public
  import A = Api`Shallow
  lemma {:induction false} Prove(s: seq<int>, t: seq<int>)
    ensures K.Rev(s+t) == K.Rev(t)+K.Rev(s)
    decreases |s|
  {
    if |s| == 0 {
      A.Empty(s);
      assert s == [];
    } else {
      Prove(s,t);
      A.Observe(s+t);
      A.Observe(s);
      assert (s+t)[1..] == s[1..]+t;
      assert (s+t)[0] == s[0];
    }
    assert K.Rev(s+t) == K.Rev(t)+K.Rev(s);
  }
}
