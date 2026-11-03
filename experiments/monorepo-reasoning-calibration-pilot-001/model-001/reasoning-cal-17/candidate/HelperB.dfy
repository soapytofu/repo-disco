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
  {var u1 := K.Lower(x, l);
O1.Lower(x, l);
var v1 := K.Upper(u1, h);
O2.Upper(u1, h);
A.Assemble(x, l, h, u1, v1);
var u2 := K.Lower(v1, a);
O1.Lower(v1, a);
var w2 := K.Upper(u2, b);
O2.Upper(u2, b);
A.Assemble(v1, a, b, u2, w2);
var u3 := K.Lower(x, a);
O1.Lower(x, a);
var w3 := K.Upper(u3, b);
O2.Upper(u3, b);
A.Assemble(x, a, b, u3, w3);  }
}
