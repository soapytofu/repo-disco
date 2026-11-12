include "Kernel.dfy"
include "Ops1.dfy"
include "Ops2.dfy"
include "Api.dfy"
module HelperA {
  import K = Kernel`Public
  import A = Api`Shallow
  import O1 = Ops1`Hidden
  import O2 = Ops2`Hidden
  lemma {:induction false} Prove(m: map<int,int>,n: map<int,int>,keep: set<int>)
    requires forall q :: q in m ==> q !in n
    ensures K.Restrict(K.Merge(m,n),keep) == K.Merge(K.Restrict(m,keep),K.Restrict(n,keep))
  {A.ObserveMerge(m, n);
    A.ObserveRestrict(K.Merge(m, n), keep);
    A.ObserveRestrict(m, keep);
    A.ObserveRestrict(n, keep);
    A.ObserveMerge(K.Restrict(m, keep), K.Restrict(n, keep));
    A.Equal(K.Restrict(K.Merge(m, n), keep), K.Merge(K.Restrict(m, keep), K.Restrict(n, keep)));  }
}
