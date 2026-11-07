include "Kernel.dfy"
include "HelperB.dfy"
module ClientB {
  import K = Kernel`Public
  import H = HelperB
  lemma Target(m: map<int,int>, k: int, j: int, x: int, y: int)
    ensures K.Drop(K.Put(K.Put(m,j,y),k,x),j) == (if j == k then K.Drop(m,j) else K.Put(K.Drop(m,j),k,x))
  { H.Prove(m,j,k,y,x); }
}
