include "Kernel.dfy"
include "Domains.dfy"
include "Values.dfy"
module HelperA {
  import K = Kernel`Public
  import D = Domains`Public
  import V = Values`Public
  lemma {:induction false} Prove(f1: map<int,int>, f2: map<int,int>, g: map<int,int>)
    ensures K.Compose(K.Override(f1,f2),g).Keys == K.Override(K.Compose(K.Restrict(f1,f1.Keys-f2.Keys),g),K.Compose(f2,g)).Keys
  {
  }
}
