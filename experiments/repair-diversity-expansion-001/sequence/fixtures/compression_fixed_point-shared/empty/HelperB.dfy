include "Kernel.dfy"
include "HelperA.dfy"
module HelperB {
  import K = Kernel`Public
  import H = HelperA
  lemma {:induction false} Prove(s: seq<int>)
    requires K.Clean(s)
    ensures K.Compress(s) == s
    decreases |s|
  { H.Prove(s); }
}
