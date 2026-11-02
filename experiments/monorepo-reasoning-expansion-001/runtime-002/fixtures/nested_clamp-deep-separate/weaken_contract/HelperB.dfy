include "Kernel.dfy"
include "Ops1.dfy"
include "Ops2.dfy"
include "Api.dfy"
module HelperB {
  import K = Kernel`Public
  import O1 = Ops1`Public
  import O2 = Ops2`Public
  import A = Api`Deep
  lemma {:induction false} Prove(x: int, l: int, h: int, a: int, b: int)
    requires l <= a <= b <= h
    ensures K.Clamp(K.Clamp(x,l,h),a,b) == K.Clamp(x,a,b)
  {
    O1.Lower(x,l);
    var u0 := if x < l then l else x;
    O2.Upper(u0,h);
    var v0 := if u0 > h then h else u0;
    A.Assemble(x,l,h,u0,v0);
    O1.Lower(K.Clamp(x,l,h),a);
    var u1 := if K.Clamp(x,l,h) < a then a else K.Clamp(x,l,h);
    O2.Upper(u1,b);
    var v1 := if u1 > b then b else u1;
    A.Assemble(K.Clamp(x,l,h),a,b,u1,v1);
    O1.Lower(x,a);
    var u2 := if x < a then a else x;
    O2.Upper(u2,b);
    var v2 := if u2 > b then b else u2;
    A.Assemble(x,a,b,u2,v2);
    assert K.Clamp(K.Clamp(x,l,h),a,b) == K.Clamp(x,a,b);
  }
}
