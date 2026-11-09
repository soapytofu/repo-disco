include "Kernel.dfy"
include "Ops1.dfy"
include "Ops2.dfy"
include "Api.dfy"
module HelperA {
  import K = Kernel`Public
  import A = Api`Deep
  import O1 = Ops1`Public
  import O2 = Ops2`Public
  lemma {:induction false} Prove(s: seq<int>,i: int,j: int)
    requires 0<=i<=|s| && 0<=j<=|s|-i
    ensures K.Prefix(s,i+j)==K.Prefix(s,i)+K.Prefix(s[i..],j)
    decreases i
  {
    if i==0 {

      assert s[0..]==s;
    } else {
      O1.Unfold(s,i+j); O2.Expose(s,i+j);
      O1.Unfold(s,i); O2.Expose(s,i);
      Prove(s[1..],i-1,j);
      assert (s[1..])[i-1..]==s[i..];
    }
  }
}
