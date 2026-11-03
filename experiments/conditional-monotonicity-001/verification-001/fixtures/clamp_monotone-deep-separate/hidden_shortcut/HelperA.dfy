include "Kernel.dfy"
include "Ops1.dfy"
include "Ops2.dfy"
include "Api.dfy"
module HelperA {
  import K = Kernel`Public
  import A = Api`Deep
  import O1 = Ops1`Public
  import O2 = Ops2`Public
  lemma {:induction false} Prove(x: int, y: int, l: int, h: int)
    requires x <= y && l <= h
    ensures K.Clamp(x,l,h) <= K.Clamp(y,l,h)
  {
    A.Below(x,l,h);
  }
}
