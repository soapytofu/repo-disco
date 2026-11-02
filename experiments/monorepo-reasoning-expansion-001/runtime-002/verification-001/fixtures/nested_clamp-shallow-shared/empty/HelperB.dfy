include "Kernel.dfy"
include "HelperA.dfy"
module HelperB {
  import K = Kernel`Public
  import H = HelperA
  lemma {:induction false} Prove(x: int, l: int, h: int, a: int, b: int)
    requires l <= a <= b <= h
    ensures K.Clamp(K.Clamp(x,l,h),a,b) == K.Clamp(x,a,b)
  {
    H.Prove(x,l,h,a,b);
  }
}
