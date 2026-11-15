include "Kernel.dfy"
module Api {
  export Public provides K, Equal
  export Hidden provides K, ObserveOverride
  import K = Kernel`Internal
  lemma Equal(left: map<int,int>, right: map<int,int>)
    requires left.Keys == right.Keys
    requires forall q :: q in left ==> q in right && left[q] == right[q]
    ensures left == right
  { }
  lemma ObserveOverride(m: map<int,int>, n: map<int,int>)
    ensures K.Override(m,n).Keys == m.Keys + n.Keys
    ensures forall q :: q in K.Override(m,n) ==>
      K.Override(m,n)[q] == (if q in n then n[q] else m[q])
  { reveal K.Override(); }
}
