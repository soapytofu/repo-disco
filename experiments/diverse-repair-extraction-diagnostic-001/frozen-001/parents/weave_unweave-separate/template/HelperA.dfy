include "Kernel.dfy"
include "Ops.dfy"
include "Api.dfy"
module HelperA {
  import K = Kernel`Public
  import O = Ops`Public
  import A = Api`Public
  lemma {:induction false} Prove(s: seq<int>, t: seq<int>)
    requires |s| == |t|
    ensures K.Left(K.Weave(s,t)) == s && K.Right(K.Weave(s,t)) == t
    decreases |s|
  {
  }
}
