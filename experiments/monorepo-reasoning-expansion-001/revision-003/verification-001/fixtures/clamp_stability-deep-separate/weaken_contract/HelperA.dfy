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
    ensures true
  {
    O1.Lower(x,l);
    var u0 := if x < l then l else x;
    O2.Upper(u0,h);
    var v0 := if u0 > h then h else u0;
    A.Assemble(x,l,h,u0,v0);
    O1.Lower((x+delta),l);
    var u1 := if (x+delta) < l then l else (x+delta);
    O2.Upper(u1,h);
    var v1 := if u1 > h then h else u1;
    A.Assemble((x+delta),l,h,u1,v1);
    assert 0 <= K.Clamp((x)+(delta),l,h) - K.Clamp(x,l,h) <= delta;
  }
}
