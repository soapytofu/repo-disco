include "Kernel.dfy"
include "Domains.dfy"
include "Values.dfy"
include "Api.dfy"
module HelperB {
  import K = Kernel`Public
  import D = Domains`Public
  import V = Values`Public
  import A = Api`Public
  lemma {:induction false} Prove(m: map<int,int>, n: map<int,int>, keep: set<int>)
    ensures K.Restrict(K.Override(m,n),keep) == K.Override(K.Restrict(m,keep),K.Restrict(n,keep))
  {
  }
}
