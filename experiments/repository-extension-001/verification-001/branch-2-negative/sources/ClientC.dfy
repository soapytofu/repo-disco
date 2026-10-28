include "Facts.dfy"
module ClientC {
  import F = Facts`ViewA
  lemma Extend(x: int, y: int)
    ensures F.Good(F.Wrap(if x - y - y >= 0 then (x - y - y) else -(x - y - y)))
  {
    if x - y - y > 0 {
      F.Case0A(x - y - y);
    } else {
      F.Case1A(x - y - y);
    }
  }
}
