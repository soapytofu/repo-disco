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
    var inner := K.Put(m,p,m[q]);
    var swapped := K.Exchange(m,p,q);
    O.ExchangeShape(m,p,q);
    O.PutKeys(m,p,m[q]);
    assert inner.Keys == m.Keys;
    O.PutKeys(inner,q,m[p]);
    assert swapped.Keys == m.Keys;
    forall x | x in m ensures x in swapped &&
      swapped[x] == (if x == p then m[q] else if x == q then m[p] else m[x]) {
      O.PutAt(inner,q,m[p],x);
      O.PutAt(m,p,m[q],x);
      if x == q {
        assert swapped[x] == m[p];
      } else if x == p {
        assert swapped[x] == m[q];
      } else {
        assert swapped[x] == m[x];
      }
    }
  }
}
