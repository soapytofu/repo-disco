include "Bounds.dfy"
include "Transform.dfy"
module Client {
  import B = Bounds
  import T = Transform
  lemma Progress(x: int)
    requires 0 <= x <= 10
    ensures T.Shift(x) > x
  {
  }
}
