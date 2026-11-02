include "Kernel.dfy"
module Api {
  export Shallow provides K, ObservePut, ObserveDrop, Equal
  export Deep provides K, Equal
  import K = Kernel`Internal
  lemma ObservePut(m: map<int,int>, k: int, v: int)
    ensures K.Put(m,k,v) == m[k := v]
  { reveal K.Put(); }
  lemma ObserveDrop(m: map<int,int>, k: int)
    ensures K.Drop(m,k) == (map q | q in m && q != k :: m[q])
  { reveal K.Drop(); }
  lemma Equal(a: map<int,int>, b: map<int,int>)
    requires a.Keys == b.Keys
    requires forall q :: q in a ==> q in b && a[q] == b[q]
    ensures a == b
  { }
}
