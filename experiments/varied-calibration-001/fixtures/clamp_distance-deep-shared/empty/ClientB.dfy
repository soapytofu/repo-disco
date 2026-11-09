include "Kernel.dfy"
include "HelperB.dfy"
module ClientB {
  import K = Kernel`Public
  import H = HelperB
  lemma Target(l: int,h: int,x: int,y: int,eps: int)
    requires l<=h && K.Abs(x-y)<=eps
    ensures K.Abs(K.Clamp(l,h,x)-K.Clamp(l,h,y))<=eps
  { H.Prove(l,h,x,y); }
}
