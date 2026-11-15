include "HelperB.dfy"
module ClientB {
  import K = Kernel`Public
  import H = HelperB
  lemma {:induction false} Target(m: map<int,int>, n: map<int,int>, keep: set<int>)
    ensures K.Restrict(K.Override(n,m),keep) == K.Override(K.Restrict(n,keep),K.Restrict(m,keep))
  { H.Prove(n,m,keep); }
}
