include "Kernel.dfy"
module Values {
  export Public provides K, OverrideAt, RestrictAt
  import K = Kernel`Internal
  lemma OverrideAt(m: map<int,int>, n: map<int,int>, q: int)
    requires q in m || q in n
    ensures q in K.Override(m,n)
    ensures K.Override(m,n)[q] == (if q in n then n[q] else m[q])
  { reveal K.Override(); }
  lemma RestrictAt(m: map<int,int>, keep: set<int>, q: int)
    requires q in m && q in keep
    ensures q in K.Restrict(m,keep)
    ensures K.Restrict(m,keep)[q] == m[q]
  { reveal K.Restrict(); }
}
