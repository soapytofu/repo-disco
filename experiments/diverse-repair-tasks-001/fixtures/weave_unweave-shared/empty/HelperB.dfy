include "HelperA.dfy"
module HelperB {
  import K = Kernel`Public
  import H = HelperA
  lemma {:induction false} Prove(s: seq<int>, t: seq<int>)
    requires |s| == |t|
    ensures K.Left(K.Weave(s,t)) == s && K.Right(K.Weave(s,t)) == t
    decreases |s|
  { H.Prove(s,t); }
}
