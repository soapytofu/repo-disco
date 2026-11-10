include "Kernel.dfy"
module Api {
  export Shallow provides K, ObserveSwap, Equal
  export Deep provides K, Equal
  import K = Kernel`Internal
  lemma ObserveSwap(m: map<int,int>,k: int,j: int)
    requires k in m && j in m
    ensures K.Swap(m,k,j).Keys == m.Keys
    ensures forall q :: q in m ==> q in K.Swap(m,k,j) && K.Swap(m,k,j)[q] == (if q==k then m[j] else if q==j then m[k] else m[q])
  { reveal K.Swap(); if k==j { assert m[k]==m[j]; } }
  lemma Equal(a: map<int,int>,b: map<int,int>)
    requires a.Keys==b.Keys
    requires forall q :: q in a ==> q in b && a[q]==b[q]
    ensures a==b
  { }
}
