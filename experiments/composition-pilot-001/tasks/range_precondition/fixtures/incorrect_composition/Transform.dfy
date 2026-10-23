include "Bounds.dfy"
module Transform {
  import B = Bounds
  export provides B, Shift, EvaluateShift
  opaque function Shift(x: int): int {
    if 0 <= x <= 10 then x + 1 else 0
  }

  lemma EvaluateShift(x: int)
    requires B.Ready(x)
    ensures Shift(x) == x + 1
  {
    B.ExposeReady(x);
    reveal Shift();
  }
}
