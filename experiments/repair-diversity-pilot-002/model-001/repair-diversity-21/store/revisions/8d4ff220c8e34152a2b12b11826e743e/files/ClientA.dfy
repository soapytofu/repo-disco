include "HelperA.dfy"
module ClientA {
  import K = Kernel`Public
  import H = HelperA
  lemma {:induction false} Target(m: map<int,int>, n: map<int,int>, keep: set<int>)
    ensures K.Restrict(K.Override(m,n),keep) == K.Override(K.Restrict(m,keep),K.Restrict(n,keep))
  { H.Prove(m,n,keep); }
}
