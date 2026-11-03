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
  }
}
