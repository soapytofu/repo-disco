include "Kernel.dfy"
include "Ops1.dfy"
include "Ops2.dfy"
include "Api.dfy"
module HelperA {
  import K = Kernel`Public
  import A = Api`Shallow
  import O1 = Ops1`Hidden
  import O2 = Ops2`Hidden
  lemma {:induction false} Prove(x: int, y: int, l: int, h: int)
    requires x <= y && l <= h
    ensures K.Clamp(x,l,h) <= K.Clamp(y,l,h)
  {
  }
}
