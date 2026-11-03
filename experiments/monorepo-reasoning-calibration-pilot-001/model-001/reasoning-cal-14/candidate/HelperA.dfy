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
  {var lx := K.Lower(x, l);
    var lxd := K.Lower(x + delta, l);
    O1.Lower(x, l);
    O1.Lower(x + delta, l);
    var ux := K.Upper(lx, h);
    var uxd := K.Upper(lxd, h);
    O2.Upper(lx, h);
    O2.Upper(lxd, h);
    A.Assemble(x, l, h, lx, ux);
    A.Assemble(x + delta, l, h, lxd, uxd);  }
}
