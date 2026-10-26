include "Facts.dfy"
module ClientB {
  import F = Facts`ViewA
  lemma Prove(x: int, y: int)
    ensures F.Good(F.Wrap(if (x - y) >= 0 then (x - y) else -(x - y)))
  {
  }
}
