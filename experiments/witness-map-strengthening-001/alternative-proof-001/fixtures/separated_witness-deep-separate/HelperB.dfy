include "Kernel.dfy"
include "Ops1.dfy"
include "Ops2.dfy"
include "Api.dfy"
module HelperB {
  import K = Kernel`Public
  import A = Api`Deep
  import O1 = Ops1`Public
  import O2 = Ops2`Public
  lemma {:induction false} Prove(a: int, b: int, c: int, d: int, gap: int)
    requires 0 < gap
    requires a + gap <= b && c + gap <= d && a + gap <= d && c + gap <= b
    ensures K.Room(a,b,c,d,gap)
  {    var v := if b <= d then b else d;
    var u := v - gap;
    O1.Right(c,d,v); O1.Left(a,b,v); O2.Join(a,b,c,d,v);
    O1.Separate(u,v,gap);
    O1.Right(c,d,u); O1.Left(a,b,u); O2.Join(a,b,c,d,u);
    A.Finish(a,b,c,d,gap,u,v);
  }
}
