include "Kernel.dfy"
include "HelperA.dfy"
module HelperB {
  import K = Kernel`Public
  import H = HelperA
  lemma {:induction false} Prove(m: map<int,int>, n: map<int,int>, p: int, q: int)
    requires K.Inverse(m,n)
    requires p in m && q in m && p != q
    ensures K.Inverse(K.Exchange(m,p,q),K.Exchange(n,m[p],m[q]))
  {
  }
}
