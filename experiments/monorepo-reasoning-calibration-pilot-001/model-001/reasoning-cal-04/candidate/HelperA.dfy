include "Kernel.dfy"
include "Ops1.dfy"
include "Ops2.dfy"
include "Api.dfy"
module HelperA {
  import K = Kernel`Public
  import O1 = Ops1`Public
  import O2 = Ops2`Public
  import A = Api`Deep
  lemma {:induction false} Prove(x: int, delta: int, l: int, h: int)
    requires delta >= 0 && l <= h
    ensures 0 <= K.Clamp((x)+(delta),l,h) - K.Clamp(x,l,h) <= delta
  {var u1 := K.Lower(x, l);
    var v1 := K.Upper(u1, h);
    O1.Lower(x, l);
    O2.Upper(u1, h);
    A.Assemble(x, l, h, u1, v1);
    var u2 := K.Lower(x + delta, l);
    var v2 := K.Upper(u2, h);
    O1.Lower(x + delta, l);
    O2.Upper(u2, h);
    A.Assemble(x + delta, l, h, u2, v2);  }
}
