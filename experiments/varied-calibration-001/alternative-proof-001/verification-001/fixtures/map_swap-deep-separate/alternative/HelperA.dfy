include "Kernel.dfy"
include "Ops1.dfy"
include "Ops2.dfy"
include "Api.dfy"
module HelperA {
  import K = Kernel`Public
  import A = Api`Deep
  import O1 = Ops1`Public
  import O2 = Ops2`Public
  lemma {:induction false} Prove(m: map<int,int>,k: int,j: int)
    requires k in m && j in m
    ensures K.Swap(K.Swap(m,k,j),k,j)==m
  {
    var once := K.Swap(m,k,j);
    var twice := K.Swap(once,k,j);
    if k==j {
      O1.Certify(m,k,j); O2.SwapKeys(m,k,j);
      forall q | q in m ensures q in once && m[q]==once[q] {
        O2.SwapAt(m,k,j,q);
      }
      A.Equal(m,once);
      assert twice==m;
    } else {
      O1.Certify(m,k,j); O2.SwapKeys(m,k,j);
      O1.Certify(once,k,j); O2.SwapKeys(once,k,j);
      forall q | q in m ensures q in twice && m[q]==twice[q] {
        if q==k { O2.SwapAt(m,k,j,j); }
        else if q==j { O2.SwapAt(m,k,j,k); }
        else { O2.SwapAt(m,k,j,q); }
        O2.SwapAt(once,k,j,q);
      }
      A.Equal(m,twice);
    }
  }
}
