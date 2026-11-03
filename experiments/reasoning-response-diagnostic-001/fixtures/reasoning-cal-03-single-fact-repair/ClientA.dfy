include "Kernel.dfy"
include "HelperA.dfy"
module ClientA {
  import K = Kernel`Public
  import H = HelperA
  lemma Use(m: map<int,int>, k: int, j: int, x: int, y: int)
    requires k != j
    ensures K.Put(K.Put(m,k,x),j,y) == K.Put(K.Put(m,j,y),k,x)
  { H.Prove(m,k,j,x,y); }
}
