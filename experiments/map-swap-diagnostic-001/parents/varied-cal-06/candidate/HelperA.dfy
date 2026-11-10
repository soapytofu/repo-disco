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
  {var u := a;
    var v := t - a;
    if c <= v <= d {
      O1.Left(a, b, u);
      O1.Right(c, d, v);
      O1.Balance(t, u, v);
      O2.Join(a, b, c, d, u, v);
      A.Finish(a, b, c, d, t, u, v);
    } else {
      if v < c {
        var u2 := t - c;
        var v2 := c;
        O1.Left(a, b, u2);
        O1.Right(c, d, v2);
        O1.Balance(t, u2, v2);
        O2.Join(a, b, c, d, u2, v2);
        A.Finish(a, b, c, d, t, u2, v2);
      } else {
        var u3 := t - d;
        var v3 := d;
        O1.Left(a, b, u3);
        O1.Right(c, d, v3);
        O1.Balance(t, u3, v3);
        O2.Join(a, b, c, d, u3, v3);
        A.Finish(a, b, c, d, t, u3, v3);
      }
    }  }
}
