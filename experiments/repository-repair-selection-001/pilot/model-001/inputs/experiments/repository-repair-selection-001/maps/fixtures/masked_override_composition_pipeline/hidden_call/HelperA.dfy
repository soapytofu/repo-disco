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
    assert left.Keys <= merged.Keys;
    assert right.Keys <= merged.Keys;
    forall x | x in merged ensures (x in left) == (x in right) {
      V.OverrideAt(f1,f2,x);
      if x in f2 {
        assert x !in trimmed;
      } else {
        V.HiddenRestrictAt(f1,keep,x);
      }
    }
    assert left.Keys == right.Keys;
  }
}
