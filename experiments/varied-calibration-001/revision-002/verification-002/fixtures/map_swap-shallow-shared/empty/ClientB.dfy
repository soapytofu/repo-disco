include "Kernel.dfy"
include "HelperB.dfy"
module ClientB {
  import K = Kernel`Public
  import H = HelperB
  lemma Target(m: map<int,int>,k: int,j: int,q: int)
    requires k in m && j in m && q in m
    ensures q in K.Swap(K.Swap(m,j,k),j,k) && K.Swap(K.Swap(m,j,k),j,k)[q]==m[q]
  { H.Prove(m,j,k); }
}
