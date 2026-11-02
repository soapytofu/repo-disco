include "Kernel.dfy"
include "Ops1.dfy"
include "Ops2.dfy"
include "Api.dfy"
module HelperA {
  import K = Kernel`Public
  import O1 = Ops1`Public
  import O2 = Ops2`Public
  import A = Api`Deep
  lemma {:induction false} Prove(x: int, delta: int, l: int, h: int)
    requires delta >= 0 && l <= h
    ensures 0 <= K.Clamp((x)+(delta),l,h) - K.Clamp(x,l,h) <= delta
  {
  }
}
