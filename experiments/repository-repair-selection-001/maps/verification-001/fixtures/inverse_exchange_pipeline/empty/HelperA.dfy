include "Kernel.dfy"
include "Ops.dfy"
module HelperA {
  import K = Kernel`Public
  import O = Ops`Public
  lemma {:induction false} Prove(m: map<int,int>, p: int, q: int)
    requires p in m && q in m && p != q
    ensures K.Exchange(m,p,q).Keys == m.Keys
    ensures forall x :: x in m ==> x in K.Exchange(m,p,q) &&
      K.Exchange(m,p,q)[x] == (if x == p then m[q] else if x == q then m[p] else m[x])
  {
  }
}
