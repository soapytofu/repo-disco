include "Kernel.dfy"
include "HelperB.dfy"
module ClientB {
  import K = Kernel`Public
  import H = HelperB
  lemma Use(m: map<int,int>, k: int, j: int, v: int)
    requires k in m && j in m && K.Valid(m) && 0 <= v <= m[j]
    ensures K.Valid(K.Move(m,j,k,v)) && K.Transfer(m,K.Move(m,j,k,v),j,k,v)
  { H.Prove(m,j,k,v); }
}
