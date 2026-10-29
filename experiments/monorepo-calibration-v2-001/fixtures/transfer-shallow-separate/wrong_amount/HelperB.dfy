include "Kernel.dfy"
include "Stage1.dfy"
include "Stage2.dfy"
include "Stage3.dfy"
module HelperB {
  import K = Kernel`Public
  import End = Stage3`Shallow
  lemma {:induction false} Prove(m: map<int,int>, k: int, j: int, v: int)
    requires k in m && j in m
    requires K.Valid(m) && 0 <= v <= m[k]
    ensures K.Valid(K.Move(m,k,j,v)) && K.Transfer(m,K.Move(m,k,j,v),k,j,v)
  {
    if k == j {
      End.Alias(m,k,j,v + 1);
    } else {
      End.Direct(m,k,j,v + 1);
    }
  }
}
