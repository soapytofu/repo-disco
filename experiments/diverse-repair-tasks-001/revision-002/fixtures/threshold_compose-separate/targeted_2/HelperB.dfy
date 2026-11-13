include "Kernel.dfy"
include "Ops.dfy"
module HelperB {
  import K = Kernel`Public
  import O = Ops`Public
  lemma {:induction false} Prove(s: int, t: int, x: int)
    requires 0 <= s && 0 <= t
    ensures K.Cut(s,K.Cut(t,x)) == K.Cut(s+t,x)
  {
    if x <= t {
      O.Below(t,x); O.Below(s,0); 
    } else if x <= s+t {
      O.Above(t,x); O.Below(s,x-t); 
    } else {
      O.Above(t,x); O.Above(s,x-t); O.Above(s+t,x);
    }
  }
}
