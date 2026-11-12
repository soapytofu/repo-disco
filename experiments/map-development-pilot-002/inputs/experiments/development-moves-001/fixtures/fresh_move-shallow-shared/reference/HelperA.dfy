include "Kernel.dfy"
include "Ops1.dfy"
include "Ops2.dfy"
include "Api.dfy"
module HelperA {
  import K = Kernel`Public
  import A = Api`Shallow
  import O1 = Ops1`Hidden
  import O2 = Ops2`Hidden
  lemma {:induction false} Prove(m: map<int,int>,a: int,b: int,c: int)
    requires a in m && b !in m && c !in m
    requires a != b && b != c && a != c
    ensures K.Move(K.Move(m,a,b),b,c) == K.Move(m,a,c)
  {
    var mid := K.Move(m,a,b);
    var left := K.Move(mid,b,c);
    var right := K.Move(m,a,c);
    A.ObserveMove(m,a,b);
    A.ObserveMove(mid,b,c);
    A.ObserveMove(m,a,c);
    assert left.Keys == right.Keys;
    forall q | q in left ensures q in right && left[q] == right[q] {
    }
    A.Equal(left,right);
  }
}
