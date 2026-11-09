include "Kernel.dfy"
include "Ops1.dfy"
include "Ops2.dfy"
include "Api.dfy"
module HelperA {
  import K = Kernel`Public
  import A = Api`Deep
  import O1 = Ops1`Public
  import O2 = Ops2`Public
  lemma {:induction false} Prove(a: int,b: int,c: int,d: int,t: int)
    requires a<=b && c<=d && a+c<=t<=b+d
    ensures K.Feasible(a,b,c,d,t)
  {
    var u := if a >= t-d then a else t-d;
    var w := t-u+1;
    O1.Left(a,b,u); O1.Right(c,d,w);
    O2.Join(a,b,c,d,u,w); O1.Balance(t,u,w);
    A.Finish(a,b,c,d,t,u,w);
  }
}
