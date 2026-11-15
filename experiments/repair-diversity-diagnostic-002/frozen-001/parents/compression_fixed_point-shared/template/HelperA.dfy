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
  }
}
