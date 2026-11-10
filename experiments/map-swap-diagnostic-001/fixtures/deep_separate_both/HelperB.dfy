include "Kernel.dfy"
include "Ops1.dfy"
include "Ops2.dfy"
include "Api.dfy"
module HelperB {
  import K = Kernel`Public
  import A = Api`Deep
  import O1 = Ops1`Public
  import O2 = Ops2`Public
  lemma {:induction false} Prove(m: map<int,int>,k: int,j: int)
    requires k in m && j in m
    ensures K.Swap(K.Swap(m,k,j),k,j)==m
  {O1.Certify(m, k, j);
    O2.SwapKeys(m, k, j);
    var m1 := K.Swap(m, k, j);
    O1.Certify(m1, k, j);
    O2.SwapKeys(m1, k, j);
    forall q | q in m ensures q in K.Swap(m1, k, j) && K.Swap(m1, k, j)[q] == m[q] {
      O2.SwapAt(m, k, j, k);
      O2.SwapAt(m, k, j, j);
      O2.SwapAt(m, k, j, q);
      O2.SwapAt(m1, k, j, q);
    }
    A.Equal(K.Swap(m1, k, j), m);  }
}
