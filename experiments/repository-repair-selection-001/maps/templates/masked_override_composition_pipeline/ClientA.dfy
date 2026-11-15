include "HelperB.dfy"
module ClientA {
  import K = Kernel`Public
  import H = HelperB
  lemma {:induction false} Target(f1: map<int,int>, f2: map<int,int>, g: map<int,int>)
    ensures K.Compose(K.Override(f1,f2),g) == K.Override(K.Compose(K.Restrict(f1,f1.Keys-f2.Keys),g),K.Compose(f2,g))
  { H.Prove(f1,f2,g); }
}
