include "MagnitudeFacts.dfy"

module Client {
  import F = MagnitudeFacts

  lemma ClientNonnegative(x: int)
    ensures F.Magnitude(x) >= 0
  {
    assert F.Magnitude(x) >= 0;
  }
}
