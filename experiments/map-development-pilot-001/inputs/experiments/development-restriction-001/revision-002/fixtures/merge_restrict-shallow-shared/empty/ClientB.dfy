include "Kernel.dfy"
include "HelperB.dfy"
module ClientB {
  import K = Kernel`Public
  import H = HelperB
  lemma Target(m: map<int,int>,n: map<int,int>,keep: set<int>,q: int)
    requires forall k :: k in m ==> k !in n
    requires q in K.Restrict(K.Merge(m,n),keep)
    ensures q in K.Merge(K.Restrict(m,keep),K.Restrict(n,keep))
    ensures K.Merge(K.Restrict(m,keep),K.Restrict(n,keep))[q] == K.Restrict(K.Merge(m,n),keep)[q]
  { H.Prove(m,n,keep); }
}
