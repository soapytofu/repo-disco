include "Kernel.dfy"
include "Ops.dfy"
include "Api.dfy"
module HelperB {
  import K = Kernel`Public
  import O = Ops`Public
  import A = Api`Public
  lemma {:induction false} Prove(a: int, b: int, c: int, d: int, gap: int)
    requires 0 < gap && a <= b && c <= d && a + gap <= d && c <= b + gap
    ensures K.Feasible(a,b,c,d,gap)
  {
    var u := if a + gap < c then c - gap else a;
    var v := u + gap;
    O.Left(a,b,u);
    O.Right(c,d,v);
    O.Offset(gap,u,v);
    A.Finish(a,b,c,d,gap,u,v);
  }
}
