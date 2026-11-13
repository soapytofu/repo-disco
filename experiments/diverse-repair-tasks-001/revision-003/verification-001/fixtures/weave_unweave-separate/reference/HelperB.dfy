include "Kernel.dfy"
include "Ops.dfy"
include "Api.dfy"
module HelperB {
  import K = Kernel`Public
  import O = Ops`Public
  import A = Api`Public
  lemma {:induction false} Prove(s: seq<int>, t: seq<int>)
    requires |s| == |t|
    ensures K.Left(K.Weave(s,t)) == s && K.Right(K.Weave(s,t)) == t
    decreases |s|
  {
    if |s| == 0 {
      A.Empty(s,t);
    } else {
      O.Unfold(s,t);
      A.Project(s[0],t[0],K.Weave(s[1..],t[1..]));
      Prove(s[1..],t[1..]);
      assert s == [s[0]] + s[1..];
      assert t == [t[0]] + t[1..];
    }
  }
}
