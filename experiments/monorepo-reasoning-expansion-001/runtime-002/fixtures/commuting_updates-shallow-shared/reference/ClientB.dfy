include "Kernel.dfy"
include "HelperB.dfy"
module ClientB {
  import K = Kernel`Public
  import H = HelperB
  lemma Use(m: map<int,int>, k: int, j: int, x: int, y: int)
    requires k != j
    ensures K.Put(K.Put(m,j,y+1),k,x-1) == K.Put(K.Put(m,k,x-1),j,y+1)
  { H.Prove(m,j,k,y+1,x-1); }
}
