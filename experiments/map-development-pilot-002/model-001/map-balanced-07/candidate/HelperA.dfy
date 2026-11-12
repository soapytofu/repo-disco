include "Kernel.dfy"
include "Ops1.dfy"
include "Ops2.dfy"
include "Api.dfy"
module HelperA {
  import K = Kernel`Public
  import A = Api`Deep
  import O1 = Ops1`Public
  import O2 = Ops2`Public
  lemma {:induction false} Prove(m: map<int,int>,a: int,b: int,c: int)
    requires a in m && b !in m && c !in m
    requires a != b && b != c && a != c
    ensures K.Move(K.Move(m,a,b),b,c) == K.Move(m,a,c)
  {O1.Certify(m, a, b);
    O2.MoveKeys(m, a, b);
    var m1 := K.Move(m, a, b);
    O1.Certify(m1, b, c);
    O2.MoveKeys(m1, b, c);
    O1.Certify(m, a, c);
    O2.MoveKeys(m, a, c);
    var m2 := K.Move(m1, b, c);
    var m3 := K.Move(m, a, c);
    forall q0 | q0 in m2 ensures q0 in m3 && m2[q0] == m3[q0] {
      if q0 == c {
        O2.MoveAt(m1, b, c, c);
        O2.MoveAt(m, a, b, b);
        O2.MoveAt(m, a, c, c);
      } else {
        O2.MoveAt(m1, b, c, q0);
        O2.MoveAt(m, a, b, q0);
        O2.MoveAt(m, a, c, q0);
      }
    }
    forall q1 | q1 in m3 ensures q1 in m2 && m3[q1] == m2[q1] {
      if q1 == c {
        O2.MoveAt(m, a, c, c);
        O2.MoveAt(m, a, b, b);
        O2.MoveAt(m1, b, c, c);
      } else {
        O2.MoveAt(m, a, c, q1);
        O2.MoveAt(m, a, b, q1);
        O2.MoveAt(m1, b, c, q1);
      }
    }
    A.Equal(m2, m3);  }
}
