include "Kernel.dfy"
include "Stage1.dfy"
include "Stage2.dfy"
include "Stage3.dfy"
module HelperA {
  import K = Kernel`Public
  import S1 = Stage1`Public
  import S2 = Stage2`Public
  import End = Stage3`Deep
  lemma {:induction false} Prove(m: map<int,int>, k: int, j: int, v: int)
    requires k in m && j in m
    requires K.Valid(m) && 0 <= v <= m[k]
    ensures K.Valid(K.Move(m,k,j,v)) && K.Transfer(m,K.Move(m,k,j,v),k,j,v)
  {
    if k == j {
      End.Alias(m,j,k,v);
    } else {
      S1.Debit(m,j,k,v);
      S2.Credit(m,j,k,v);
      End.Finish(m,j,k,v);
    }
  }
}
