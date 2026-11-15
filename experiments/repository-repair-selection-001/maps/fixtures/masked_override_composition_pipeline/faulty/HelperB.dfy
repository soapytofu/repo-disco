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
    H.Prove(f1,f2,g);
    var keep := f1.Keys-f2.Keys;
    var merged := K.Override(f1,f2);
    var trimmed := K.Restrict(f1,keep);
    var left := K.Compose(merged,g);
    var first := K.Compose(trimmed,g);
    var second := K.Compose(f2,g);
    var right := K.Override(first,second);
    D.OverrideKeys(f1,f2);
    D.RestrictKeys(f1,keep);
    D.ComposeKeys(merged,g);
    D.ComposeKeys(trimmed,g);
    D.ComposeKeys(f2,g);
    D.OverrideKeys(first,second);
    forall x | x in left ensures x in right && left[x] == right[x] {
      V.OverrideAt(f1,f2,x);
      V.ComposeAt(merged,g,x);
      if x in f2 {
        V.ComposeAt(f2,g,x);
      } else {
        V.RestrictAt(f1,keep,x);
        V.ComposeAt(trimmed,g,x);
      }
      V.OverrideAt(first,second,x);
    }
    A.Equal(left,right);
  }
}
