include "Kernel.dfy"
module Ops1 {
  export Hidden provides K
  export Public provides K, Unfold
  import K = Kernel`Internal
  lemma Unfold(s: seq<int>,n: int)
    requires 0<=n<=|s|
    ensures K.StepFact(s,n)
  {
    reveal K.StepFact(); reveal K.Prefix(); reveal K.Total();
    if n==0 { assert s[..0]==[]; }
    else {
      assert |s[..n]|>0;
      assert (s[..n])[0]==s[0];
      assert (s[..n])[1..] == (s[1..])[..n-1];
    }
  }
}
