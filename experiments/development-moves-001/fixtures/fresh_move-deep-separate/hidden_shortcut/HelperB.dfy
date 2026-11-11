include "Kernel.dfy"
include "Ops1.dfy"
include "Ops2.dfy"
include "Api.dfy"
module HelperB {
  import K = Kernel`Public
  import A = Api`Deep
  import O1 = Ops1`Public
  import O2 = Ops2`Public
  lemma {:induction false} Prove(m: map<int,int>,a: int,b: int,c: int)
    requires a in m && b !in m && c !in m
    requires a != b && b != c && a != c
    ensures K.Move(K.Move(m,a,b),b,c) == K.Move(m,a,c)
  {
    A.ObserveMove(m,a,b);
  }
}
