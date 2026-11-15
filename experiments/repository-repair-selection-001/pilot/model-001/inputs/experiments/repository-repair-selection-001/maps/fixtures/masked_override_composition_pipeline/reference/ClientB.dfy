include "HelperB.dfy"
module ClientB {
  import K = Kernel`Public
  import H = HelperB
  lemma {:induction false} Target(f1: map<int,int>, f2: map<int,int>, g: map<int,int>)
    ensures K.Compose(K.Override(f2,f1),g) == K.Override(K.Compose(K.Restrict(f2,f2.Keys-f1.Keys),g),K.Compose(f1,g))
  { H.Prove(f2,f1,g); }
}
