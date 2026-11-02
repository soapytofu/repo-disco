include "Kernel.dfy"
include "HelperA.dfy"
module ClientA {
  import K = Kernel`Public
  import H = HelperA
  lemma Use(m: map<int,int>, k: int, j: int, v: int)
    requires k in m && j in m && K.Valid(m) && 0 <= v <= m[k]
    ensures K.Valid(K.Move(m,k,j,v)) && K.Transfer(m,K.Move(m,k,j,v),k,j,v)
  { H.Prove(m,k,j,v); }
}
