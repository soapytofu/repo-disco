include "Kernel.dfy"
include "HelperA.dfy"
module ClientA {
  import K = Kernel`Public
  import H = HelperA
  lemma Target(m: map<int,int>,n: map<int,int>,keep: set<int>)
    requires forall q :: q in m ==> q !in n
    ensures K.Restrict(K.Merge(m,n),keep) == K.Merge(K.Restrict(m,keep),K.Restrict(n,keep))
  { H.Prove(m,n,keep); }
}
