include "Kernel.dfy"
include "Ops1.dfy"
include "Ops2.dfy"
include "Api.dfy"
module HelperB {
  import K = Kernel`Public
  import A = Api`Shallow
  import O1 = Ops1`Hidden
  import O2 = Ops2`Hidden
  lemma {:induction false} Prove(l: int,h: int,x: int,y: int)
    requires l<=h
    ensures K.Abs(K.Clamp(l,h,x)-K.Clamp(l,h,y)) <= K.Abs(x-y)
  {
    if x<=l { A.Below(l,h,x); }
    else if x<=h { A.Within(l,h,x); }
    else { A.Above(l,h,x); }
    if y<l { A.Below(l,h,y); }
    else if y<=h { A.Within(l,h,y); }
    else { A.Above(l,h,y); }
    if x<=y {
      assert K.Clamp(l,h,x)<=K.Clamp(l,h,y);
      assert K.Clamp(l,h,y)-K.Clamp(l,h,x)<=y-x;
    } else {
      assert K.Clamp(l,h,y)<=K.Clamp(l,h,x);
      assert K.Clamp(l,h,x)-K.Clamp(l,h,y)<=x-y;
    }
  }
}
