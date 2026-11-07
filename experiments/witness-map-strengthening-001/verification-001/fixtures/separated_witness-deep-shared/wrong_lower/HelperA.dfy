include "Kernel.dfy"
include "Ops1.dfy"
include "Ops2.dfy"
include "Api.dfy"
module HelperA {
  import K = Kernel`Public
  import A = Api`Deep
  import O1 = Ops1`Public
  import O2 = Ops2`Public
  lemma {:induction false} Prove(a: int, b: int, c: int, d: int, gap: int)
    requires 0 < gap
    requires a + gap <= b && c + gap <= d && a + gap <= d && c + gap <= b
    ensures K.Room(a,b,c,d,gap)
  {
    var u := a;
    var v := u + gap;
    O1.Left(a,b,u); O1.Right(c,d,u); O2.Join(a,b,c,d,u);
    O1.Left(a,b,v); O1.Right(c,d,v); O2.Join(a,b,c,d,v);
    O1.Separate(u,v,gap); A.Finish(a,b,c,d,gap,u,v);
  }
}
