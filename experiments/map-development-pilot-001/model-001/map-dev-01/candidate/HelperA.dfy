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
  {A.ObserveMove(m, a, b);
    var m1 := K.Move(m, a, b);
    assert m1.Keys == (m.Keys - {a}) + {b};
    assert b in m1;
    assert c !in m1;
    assert b != c;
    A.ObserveMove(m1, b, c);
    var m2 := K.Move(m1, b, c);
    assert m2.Keys == (m1.Keys - {b}) + {c};
    A.ObserveMove(m, a, c);
    var m3 := K.Move(m, a, c);
    assert m3.Keys == (m.Keys - {a}) + {c};
    assert m2.Keys == m3.Keys;
    assert forall q0 :: q0 in m2 ==> q0 in m3 && m2[q0] == m3[q0];
    A.Equal(m2, m3);  }
}
