include "Kernel.dfy"
module Ops2 {
  export Hidden provides K
  export Public provides K, MergeKeys, MergeAt, RestrictKeys, RestrictAt
  import K = Kernel`Internal
  lemma MergeKeys(m: map<int,int>,n: map<int,int>)
    requires K.Separate(m,n)
    ensures K.Merge(m,n).Keys == m.Keys + n.Keys
  { reveal K.Merge(); }
  lemma MergeAt(m: map<int,int>,n: map<int,int>,q: int)
    requires K.Separate(m,n)
    requires q in m || q in n
    ensures q in K.Merge(m,n)
    ensures K.Merge(m,n)[q] == (if q in m then m[q] else n[q])
  { reveal K.Merge(); }
  lemma RestrictKeys(m: map<int,int>,keep: set<int>)
    ensures K.Restrict(m,keep).Keys == m.Keys - (m.Keys - keep)
  { reveal K.Restrict(); }
  lemma RestrictAt(m: map<int,int>,keep: set<int>,q: int)
    requires q in m && q in keep
    ensures q in K.Restrict(m,keep)
    ensures K.Restrict(m,keep)[q] == m[q]
  { reveal K.Restrict(); }
}
