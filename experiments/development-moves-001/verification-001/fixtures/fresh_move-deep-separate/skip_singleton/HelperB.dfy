include "Kernel.dfy"
include "Ops1.dfy"
include "Ops2.dfy"
include "Api.dfy"
module HelperB {
  import K = Kernel`Public
  import A = Api`Deep
  import O1 = Ops1`Public
  import O2 = Ops2`Public
  lemma {:induction false} Prove(m: map<int,int>,a: int,b: int,c: int)
    requires a in m && b !in m && c !in m
    requires a != b && b != c && a != c
    ensures K.Move(K.Move(m,a,b),b,c) == K.Move(m,a,c)
  {
    if |m| > 1 {
    var mid := K.Move(m,a,b);
    var left := K.Move(mid,b,c);
    var right := K.Move(m,a,c);
    O1.Certify(m,a,b); O2.MoveKeys(m,a,b);
    O1.Certify(mid,b,c); O2.MoveKeys(mid,b,c);
    O1.Certify(m,a,c); O2.MoveKeys(m,a,c);
    assert left.Keys == right.Keys;
    forall q | q in left ensures q in right && left[q] == right[q] {
      O2.MoveAt(mid,b,c,q);
      O2.MoveAt(m,a,c,q);
      if q == c { O2.MoveAt(m,a,b,b); }
      else { O2.MoveAt(m,a,b,q); }
    }
    A.Equal(left,right);
    }
  }
}
