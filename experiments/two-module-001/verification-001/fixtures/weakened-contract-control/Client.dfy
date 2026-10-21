include "Arithmetic.dfy"

module Client {
  import A = Arithmetic

  method IncrementTwice(x: int) returns (y: int)
    ensures y == x + 2
  {
    var first := A.Increment(x);
    y := A.Increment(first);
    assert first == x + 1;
    assert y == x + 2;
  }
}
