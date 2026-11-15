include "Kernel.dfy"
module Domains {
  export Public provides K, OverrideKeys, RestrictKeys, ComposeKeys
  import K = Kernel`Internal
  lemma OverrideKeys(f1: map<int,int>, f2: map<int,int>)
    ensures K.Override(f1,f2).Keys == f1.Keys + f2.Keys
  { reveal K.Override(); }
  lemma RestrictKeys(f: map<int,int>, keep: set<int>)
    ensures K.Restrict(f,keep).Keys == f.Keys * keep
  { reveal K.Restrict(); }
  lemma ComposeKeys(f: map<int,int>, g: map<int,int>)
    ensures K.Compose(f,g).Keys == (set x | x in f && f[x] in g)
  { reveal K.Compose(); }
}
