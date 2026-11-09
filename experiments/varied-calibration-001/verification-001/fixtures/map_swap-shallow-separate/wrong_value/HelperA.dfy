include "Kernel.dfy"
include "Ops1.dfy"
include "Ops2.dfy"
include "Api.dfy"
module HelperA {
  import K = Kernel`Public
  import A = Api`Shallow
  import O1 = Ops1`Hidden
  import O2 = Ops2`Hidden
  lemma {:induction false} Prove(m: map<int,int>,k: int,j: int)
    requires k in m && j in m
    ensures K.Swap(K.Swap(m,k,j),k,j)==m
  {
    var once := K.Swap(m,k,j);
    var twice := K.Swap(once,k,j);
    A.ObserveSwap(m,k,j); A.ObserveSwap(once,k,j);
    assert m.Keys == twice.Keys;
    forall q | q in m ensures q in twice && m[q]==twice[q] {
    }
    A.Equal(m,twice);
    assert once[k]==m[k];
  }
}
