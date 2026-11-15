include "Kernel.dfy"
include "HelperA.dfy"
module HelperB {
  import K = Kernel`Public
  import H = HelperA
  lemma {:induction false} Prove(m: map<int,int>, n: map<int,int>, p: int, q: int)
    requires K.Inverse(m,n)
    requires p in m && q in m && p != q
    ensures K.Inverse(K.Exchange(m,p,q),K.Exchange(n,m[p],m[q]))
  {
    var u := m[p];
    var v := m[q];
    assert u in n && v in n;
    assert n[u] == p && n[v] == q;
    assert u != v;
    H.Prove(n,u,v);
    H.Prove(m,p,q);
    var forward := K.Exchange(m,p,q);
    var backward := K.Exchange(n,u,v);
    forall y | y in backward ensures backward[y] in forward && forward[backward[y]] == y {
      assert y in n;
      assert m[n[y]] == y;
      if y == u {
        assert backward[y] == q;
        assert forward[q] == u;
      } else if y == v {
        assert backward[y] == p;
        assert forward[p] == v;
      } else {
        assert n[y] != p && n[y] != q;
        assert backward[y] == n[y];
        assert forward[n[y]] == m[n[y]];
      }
    }
    forall x | x in forward ensures forward[x] in backward && backward[forward[x]] == x {
      assert x in m;
      assert n[m[x]] == x;
      if x == p {
        assert forward[x] == v;
        assert backward[v] == p;
      } else if x == q {
        assert forward[x] == u;
        assert backward[u] == q;
      } else {
        assert m[x] != u && m[x] != v;
        assert forward[x] == m[x];
        assert backward[m[x]] == n[m[x]];
      }
    }
  }
}
