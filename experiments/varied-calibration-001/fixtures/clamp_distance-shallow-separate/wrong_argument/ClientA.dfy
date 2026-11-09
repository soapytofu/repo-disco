include "Kernel.dfy"
include "HelperA.dfy"
module ClientA {
  import K = Kernel`Public
  import H = HelperA
  lemma Target(l: int,h: int,x: int,y: int)
    requires l<=h
    ensures K.Abs(K.Clamp(l,h,x)-K.Clamp(l,h,y)) <= K.Abs(x-y)
  { H.Prove(l,h,x,y); }
}
