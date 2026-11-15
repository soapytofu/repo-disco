include "Kernel.dfy"
include "Ops.dfy"
module HelperA {
  import K = Kernel`Public
  import O = Ops`Public
  lemma {:induction false} Prove(s: seq<int>)
    requires K.Clean(s)
    ensures K.Compress(s) == s
    decreases |s|
  {
    if |s| == 0 {
      O.Base(s);
    } else if |s| == 1 {
      O.Base(s);
    } else {
      var rest := s[1..];
      O.Boundary(s);
      O.Keep(s);
      O.TailInvariant(s);
      Prove(rest);
      assert s == [s[0]] + rest;
      assert K.Compress(s) == [s[0]] + K.Compress(rest);
    }
  }
}
