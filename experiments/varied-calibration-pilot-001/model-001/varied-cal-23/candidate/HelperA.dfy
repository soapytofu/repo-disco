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
  {var u0 := a;
    var v0 := t - a;
    if c <= v0 <= d {
      O1.Left(a, b, u0);
      O1.Right(c, d, v0);
      O1.Balance(t, u0, v0);
      O2.Join(a, b, c, d, u0, v0);
      A.Finish(a, b, c, d, t, u0, v0);
    } else {
      if v0 < c {
        var u1 := t - c;
        var v1 := c;
        O1.Left(a, b, u1);
        O1.Right(c, d, v1);
        O1.Balance(t, u1, v1);
        O2.Join(a, b, c, d, u1, v1);
        A.Finish(a, b, c, d, t, u1, v1);
      } else {
        var u2 := t - d;
        var v2 := d;
        O1.Left(a, b, u2);
        O1.Right(c, d, v2);
        O1.Balance(t, u2, v2);
        O2.Join(a, b, c, d, u2, v2);
        A.Finish(a, b, c, d, t, u2, v2);
      }
    }  }
}
