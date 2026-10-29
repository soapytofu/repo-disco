include "Kernel.dfy"
include "Stage1.dfy"
include "Stage2.dfy"
include "Stage3.dfy"
module HelperA {
  import K = Kernel`Public
  import End = Stage3`Shallow
  lemma {:induction false} Prove(m: map<int,int>, k: int, j: int, v: int)
    requires k in m && j in m
    requires K.Valid(m) && 0 <= v <= m[k]
    ensures true
  {
    if k == j {
      End.Alias(m,k,j,v);
    } else {
      End.Direct(m,k,j,v);
    }
  }
}
