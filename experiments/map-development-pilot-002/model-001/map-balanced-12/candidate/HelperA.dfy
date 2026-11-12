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
    forall q | q in m2 ensures m2[q] == m3[q] {
        if q == c {
            assert m2[q] == m1[b];
            assert m1[b] == m[a];
            assert m3[q] == m[a];
        } else {
            assert q != c;
            assert q in m2.Keys;
            assert q in (m1.Keys - {b}) + {c};
            assert q in m1.Keys - {b};
            assert q != b;
            assert q in m1.Keys;
            assert m2[q] == m1[q];
            assert q in (m.Keys - {a}) + {b};
            assert q != b;
            assert q in m.Keys - {a};
            assert q != a;
            assert q in m.Keys;
            assert m1[q] == m[q];
            assert q in m3.Keys;
            assert q != c;
            assert m3[q] == m[q];
        }
    }
    A.Equal(m2, m3);  }
}
