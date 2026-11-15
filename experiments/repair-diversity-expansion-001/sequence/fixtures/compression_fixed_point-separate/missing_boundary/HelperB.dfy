include "Kernel.dfy"
include "Ops.dfy"
module HelperB {
  import K = Kernel`Public
  import O = Ops`Public
  lemma {:induction false} Prove(s: seq<int>)
    requires K.Clean(s)
    ensures K.Compress(s) == s
    decreases |s|
  {
    if |s| < 2 { O.Base(s); }
    else {
      O.TailInvariant(s); Prove(s[1..]); O.Keep(s);
      assert s == [s[0]] + s[1..];
    }
  }
}
