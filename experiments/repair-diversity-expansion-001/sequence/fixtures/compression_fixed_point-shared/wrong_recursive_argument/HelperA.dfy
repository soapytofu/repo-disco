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
    if |s| < 2 { O.Base(s); }
    else {
      O.TailInvariant(s); O.Boundary(s); O.Keep(s);
      Prove(s[2..]);
      assert s == [s[0]] + s[1..];
    }
  }
}
