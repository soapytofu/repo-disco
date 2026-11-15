include "Kernel.dfy"
include "Domains.dfy"
include "Values.dfy"
include "Api.dfy"
include "HelperA.dfy"
module HelperB {
  import K = Kernel`Public
  import D = Domains`Public
  import V = Values`Public
  import A = Api`Public
  import H = HelperA
  lemma {:induction false} Prove(m: map<int,int>, n: map<int,int>, keep: set<int>)
    ensures K.Restrict(K.Override(m,n),keep) == K.Override(K.Restrict(m,keep),K.Restrict(n,keep))
  {
    H.Prove(m,n,keep);
  }
}
