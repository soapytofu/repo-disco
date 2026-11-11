include "Kernel.dfy"
include "Ops1.dfy"
include "Ops2.dfy"
include "Api.dfy"
module HelperB {
  import K = Kernel`Public
  import A = Api`Shallow
  import O1 = Ops1`Hidden
  import O2 = Ops2`Hidden
  lemma {:induction false} Prove(m: map<int,int>,a: int,b: int,c: int)
    requires a in m && b !in m && c !in m
    requires a != b && b != c && a != c
    ensures K.Move(K.Move(m,a,b),b,c) == K.Move(m,a,c)
  {
    O1.Certify(m,a,b);
  }
}
