include "Kernel.dfy"
include "HelperB.dfy"
module ClientB {
  import K = Kernel`Public
  import H = HelperB
  lemma Use(m: map<int,int>, k: int, j: int, v: int)
    ensures K.Drop(K.Put(m,j,v+1),k) == (if j == k then K.Drop(m,k) else K.Put(K.Drop(m,k),j,v+1))
  { H.Prove(m,j,k,v+1); }
}
