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
    var merged := K.Override(m,n);
    var left := K.Restrict(merged,keep);
    var rm := K.Restrict(m,keep);
    var rn := K.Restrict(n,keep);
    var right := K.Override(rm,rn);
    D.OverrideKeys(m,n);
    D.RestrictKeys(merged,keep);
    D.RestrictKeys(m,keep);
    D.RestrictKeys(n,keep);
    D.OverrideKeys(rm,rn);
    assert left.Keys == right.Keys;
    forall q | q in left ensures q in right && left[q] == right[q] {
      V.OverrideAt(rm,rn,q);
      if q in rn {
        V.RestrictAt(n,keep,q);
      } else {
        V.RestrictAt(m,keep,q);
      }
      V.OverrideAt(m,n,q);
      V.RestrictAt(merged,keep,q);
    }
    A.Equal(left,right);
  }
}
