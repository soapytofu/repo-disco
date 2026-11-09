include "Kernel.dfy"
include "Ops1.dfy"
include "Ops2.dfy"
include "Api.dfy"
module HelperA {
  import K = Kernel`Public
  import A = Api`Deep
  import O1 = Ops1`Public
  import O2 = Ops2`Public
  lemma {:induction false} Prove(l: int,h: int,x: int,y: int)
    requires l<=h
    ensures K.Abs(K.Clamp(l,h,x)-K.Clamp(l,h,y)) <= K.Abs(x-y)
  {
    if x<l { O1.Below(l,h,x); O2.ReadBelow(l,h,x); }
    else if x<=h { O1.Within(l,h,x); O2.ReadWithin(l,h,x); }
    else { O1.Above(l,h,x); O2.ReadAbove(l,h,x); }
    if y<l { O1.Below(l,h,y); O2.ReadBelow(l,h,y); }
    else if y<=h { O1.Within(l,h,y); O2.ReadWithin(l,h,y); }
    else { O1.Above(l,h,y); O2.ReadAbove(l,h,y); }
    if x<=y {
      assert K.Clamp(l,h,x)<=K.Clamp(l,h,y);
      assert K.Clamp(l,h,y)-K.Clamp(l,h,x)<=y-x;
    } else {
      assert K.Clamp(l,h,y)<=K.Clamp(l,h,x);
      assert K.Clamp(l,h,x)-K.Clamp(l,h,y)<=x-y;
    }
  }
}
