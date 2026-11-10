include "Kernel.dfy"
module Ops2 {
  export Hidden provides K
  export Public provides K, Expose
  import K = Kernel`Internal
  lemma Expose(s: seq<int>,n: int)
    requires 0<=n<=|s|
    requires K.StepFact(s,n)
    ensures if n==0 then K.Prefix(s,n)==0 else K.Prefix(s,n)==s[0]+K.Prefix(s[1..],n-1)
  { reveal K.StepFact(); }
}
