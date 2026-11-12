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
    O1.Certify(K.Move(m, a, b), b, c);
    O2.MoveKeys(K.Move(m, a, b), b, c);
    O1.Certify(m, a, c);
    O2.MoveKeys(m, a, c);
    var left := K.Move(K.Move(m, a, b), b, c);
    var right := K.Move(m, a, c);
    assert left.Keys == (m.Keys - {a}) + {c};
    assert right.Keys == (m.Keys - {a}) + {c};
    forall q | q in left ensures q in right && left[q] == right[q] {
        if q == c {
            O2.MoveAt(K.Move(m, a, b), b, c, c);
            O2.MoveAt(m, a, b, b);
            O2.MoveAt(m, a, c, c);
            assert left[q] == m[a];
            assert right[q] == m[a];
        } else {
            assert q in m.Keys - {a};
            assert q != b;
            O2.MoveAt(m, a, b, q);
            O2.MoveAt(K.Move(m, a, b), b, c, q);
            O2.MoveAt(m, a, c, q);
            assert left[q] == m[q];
            assert right[q] == m[q];
        }
    }
    A.Equal(left, right);  }
}
