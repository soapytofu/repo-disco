include "Kernel.dfy"
module Stage3 {
  export Shallow provides K, Alias, Direct
  export Deep provides K, Alias, Finish
  import K = Kernel`Internal
  lemma Alias(m: map<int,int>, k: int, j: int, v: int)
    requires k in m && j in m && k == j && K.Valid(m)
    ensures K.Valid(K.Move(m,k,j,v)) && K.Transfer(m,K.Move(m,k,j,v),k,j,v)
  { reveal K.Transfer(); }
  lemma Direct(m: map<int,int>, k: int, j: int, v: int)
    requires k in m && j in m && k != j
    requires K.Valid(m) && 0 <= v <= m[k]
    ensures K.Valid(K.Move(m,k,j,v)) && K.Transfer(m,K.Move(m,k,j,v),k,j,v)
  { reveal K.Valid(); reveal K.Transfer(); }
  lemma Finish(m: map<int,int>, k: int, j: int, v: int)
    requires k in m && j in m && K.Credited(m,k,j,v)
    ensures K.Valid(K.Move(m,k,j,v)) && K.Transfer(m,K.Move(m,k,j,v),k,j,v)
  { reveal K.Credited(); }
}
