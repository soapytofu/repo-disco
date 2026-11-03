include "Kernel.dfy"
include "Ops1.dfy"
include "Ops2.dfy"
include "Api.dfy"
module HelperB {
  import K = Kernel`Public
  import A = Api`Deep
  import O1 = Ops1`Public
  import O2 = Ops2`Public
  lemma {:induction false} Prove(x: int, y: int, l: int, h: int)
    requires x <= y && l <= h
    ensures K.Clamp(x,l,h) <= K.Clamp(y,l,h)
  {
    if x < l {
      O1.Above(x,l,h); O2.Below(l,h); A.Assemble(x,l,h,l,l);
    } else if x <= h {
      O1.Within(x,l,h); O2.Within(x,l,h); A.Assemble(x,l,h,x,x);
    } else {
      O1.Above(x,l,h); O2.Above(x,h); A.Assemble(x,l,h,x,h);
    }
    if y < l {
      O1.Below(y,l,h); O2.Below(l,h); A.Assemble(y,l,h,l,l);
    } else if y <= h {
      O1.Within(y,l,h); O2.Within(y,l,h); A.Assemble(y,l,h,y,y);
    } else {
      O1.Above(y,l,h); O2.Above(y,h); A.Assemble(y,l,h,y,h);
    }
  }
}
