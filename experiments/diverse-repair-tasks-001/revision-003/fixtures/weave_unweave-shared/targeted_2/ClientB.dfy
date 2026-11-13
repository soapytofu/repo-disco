include "HelperB.dfy"
module ClientB {
  import K = Kernel`Public
  import H = HelperB
  lemma {:induction false} Target(s: seq<int>, t: seq<int>)
    requires |s| == |t|
    ensures K.Left(K.Weave(t,s)) == t && K.Right(K.Weave(t,s)) == s
  { H.Prove(t,s); }
}
