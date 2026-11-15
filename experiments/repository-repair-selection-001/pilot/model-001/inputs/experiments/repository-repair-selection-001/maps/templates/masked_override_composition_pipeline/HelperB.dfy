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
  lemma {:induction false} Prove(f1: map<int,int>, f2: map<int,int>, g: map<int,int>)
    ensures K.Compose(K.Override(f1,f2),g) == K.Override(K.Compose(K.Restrict(f1,f1.Keys-f2.Keys),g),K.Compose(f2,g))
  {
  }
}
