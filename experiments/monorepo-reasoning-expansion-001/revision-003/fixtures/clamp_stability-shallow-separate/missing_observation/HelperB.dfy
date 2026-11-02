include "Kernel.dfy"
include "Ops1.dfy"
include "Ops2.dfy"
include "Api.dfy"
module HelperB {
  import K = Kernel`Public
  import A = Api`Shallow
  lemma {:induction false} Prove(x: int, delta: int, l: int, h: int)
    requires delta >= 0 && l <= h
    ensures 0 <= K.Clamp((x)+(delta),l,h) - K.Clamp(x,l,h) <= delta
  {
    A.Observe(x,l,h);
    assert 0 <= K.Clamp((x)+(delta),l,h) - K.Clamp(x,l,h) <= delta;
  }
}
