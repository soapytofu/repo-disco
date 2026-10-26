include "Facts.dfy"
module ClientB {
  import F = Facts`ViewB
  lemma Prove(x: int, y: int)
    ensures F.Good(F.Wrap(if (x - y) >= 0 then (x - y) else -(x - y)))
  {
    if 0 <= (x - y) {
      F.Case0B((x - y));
    } else {
      F.Case1B((x - y));
    }
  }
}
