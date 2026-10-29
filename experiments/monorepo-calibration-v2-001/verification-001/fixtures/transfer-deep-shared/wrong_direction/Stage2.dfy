include "Kernel.dfy"
module Stage2 {
  export Public provides K, Credit
  import K = Kernel`Internal
  lemma Credit(m: map<int,int>, k: int, j: int, v: int)
    requires k in m && j in m
    requires K.Debited(m,k,j,v)
    ensures K.Credited(m,k,j,v)
  { reveal K.Debited(); reveal K.Valid(); reveal K.Credited(); reveal K.Transfer(); }
}
