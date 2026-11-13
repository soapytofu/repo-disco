include "HelperA.dfy"
module ClientA {
  import K = Kernel`Public
  import H = HelperA
  lemma {:induction false} Target(s: seq<int>, t: seq<int>)
    requires |s| == |t|
    ensures K.Left(K.Weave(s,t)) == s && K.Right(K.Weave(s,t)) == t
  { H.Prove(s,t); }
}
