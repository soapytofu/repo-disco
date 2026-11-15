include "Kernel.dfy"
module Values {
  export Public provides K, OverrideAt, RestrictAt, ComposeAt
  export Hidden provides K, HiddenRestrictAt
  import K = Kernel`Internal
  lemma OverrideAt(f1: map<int,int>, f2: map<int,int>, x: int)
    requires x in f1 || x in f2
    ensures x in K.Override(f1,f2)
    ensures K.Override(f1,f2)[x] == (if x in f2 then f2[x] else f1[x])
  { reveal K.Override(); }
  lemma RestrictAt(f: map<int,int>, keep: set<int>, x: int)
    requires x in f && x in keep
    ensures x in K.Restrict(f,keep)
    ensures K.Restrict(f,keep)[x] == f[x]
  { reveal K.Restrict(); }
  lemma ComposeAt(f: map<int,int>, g: map<int,int>, x: int)
    requires x in f && f[x] in g
    ensures x in K.Compose(f,g)
    ensures K.Compose(f,g)[x] == g[f[x]]
  { reveal K.Compose(); }
  lemma HiddenRestrictAt(f: map<int,int>, keep: set<int>, x: int)
    requires x in f && x in keep
    ensures x in K.Restrict(f,keep)
    ensures K.Restrict(f,keep)[x] == f[x]
  { reveal K.Restrict(); }
}
