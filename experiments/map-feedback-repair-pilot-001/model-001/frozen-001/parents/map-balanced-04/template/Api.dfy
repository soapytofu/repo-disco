include "Kernel.dfy"
module Api {
  export Shallow provides K, ObserveMerge, ObserveRestrict, Equal
  export Deep provides K, Equal
  import K = Kernel`Internal
  lemma ObserveMerge(m: map<int,int>,n: map<int,int>)
    requires forall q :: q in m ==> q !in n
    ensures K.Merge(m,n).Keys == m.Keys + n.Keys
    ensures forall q :: q in K.Merge(m,n) ==>
      K.Merge(m,n)[q] == (if q in m then m[q] else n[q])
  { reveal K.Separate(); reveal K.Merge(); }
  lemma ObserveRestrict(m: map<int,int>,keep: set<int>)
    ensures K.Restrict(m,keep).Keys == m.Keys - (m.Keys - keep)
    ensures forall q :: q in K.Restrict(m,keep) ==> q in m && K.Restrict(m,keep)[q] == m[q]
  { reveal K.Restrict(); }
  lemma Equal(left: map<int,int>,right: map<int,int>)
    requires left.Keys == right.Keys
    requires forall q :: q in left ==> q in right && left[q] == right[q]
    ensures left == right
  { }
}
