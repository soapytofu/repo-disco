include "HelperB.dfy"
module ClientB {
  import K = Kernel`Public
  import H = HelperB
  lemma {:induction false} Target(m: map<int,int>, n: map<int,int>, p: int, q: int)
    requires K.Inverse(m,n)
    requires p in m && q in m && p != q
    ensures K.Inverse(K.Exchange(n,m[p],m[q]),K.Exchange(m,p,q))
  {
    assert K.Inverse(n,m);
    assert n[m[p]] == p && n[m[q]] == q;
    assert m[p] != m[q];
    H.Prove(n,m,m[p],m[q]);
  }
}
