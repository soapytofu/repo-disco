include "Kernel.dfy"
include "Ops1.dfy"
include "Ops2.dfy"
include "Api.dfy"
module HelperB {
  import K = Kernel`Public
  import A = Api`Shallow
  lemma {:induction false} Prove(s: seq<int>, p: int, q: int)
    requires q <= p
    ensures K.Filter(K.Filter(s,p),q) == K.Filter(s,q)
    decreases |s|
  {
  }
}
