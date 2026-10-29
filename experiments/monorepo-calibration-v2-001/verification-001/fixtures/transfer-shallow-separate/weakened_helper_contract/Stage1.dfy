include "Kernel.dfy"
module Stage1 {
  export Public provides K, Debit
  import K = Kernel`Internal
  lemma Debit(m: map<int,int>, k: int, j: int, v: int)
    requires k in m && j in m && k != j
    requires K.Valid(m) && 0 <= v <= m[k]
    ensures K.Debited(m,k,j,v)
  { reveal K.Valid(); reveal K.Debited(); }
}
