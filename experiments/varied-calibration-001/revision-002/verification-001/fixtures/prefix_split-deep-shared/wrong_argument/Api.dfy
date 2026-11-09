include "Kernel.dfy"
include "Ops1.dfy"
include "Ops2.dfy"
module Api {
  export Shallow provides K, Observe
  export Deep provides K
  import K = Kernel`Public
  import O1 = Ops1`Public
  import O2 = Ops2`Public
  lemma Observe(s: seq<int>,n: int)
    requires 0<=n<=|s|
    ensures if n==0 then K.Prefix(s,n)==0 else K.Prefix(s,n)==s[0]+K.Prefix(s[1..],n-1)
  { O1.Unfold(s,n); O2.Expose(s,n); }
}
