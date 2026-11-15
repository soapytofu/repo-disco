include "Kernel.dfy"
module Domains {
  export Public provides K, OverrideKeys, RestrictKeys
  import K = Kernel`Internal
  lemma OverrideKeys(m: map<int,int>, n: map<int,int>)
    ensures K.Override(m,n).Keys == m.Keys + n.Keys
  { reveal K.Override(); }
  lemma RestrictKeys(m: map<int,int>, keep: set<int>)
    ensures K.Restrict(m,keep).Keys == m.Keys * keep
  { reveal K.Restrict(); }
}
