include "Facts.dfy"
module ClientA {
  import F = Facts`ViewA
  lemma Prove(x: int, y: int)
    ensures F.Good(F.Wrap(if x >= 0 then x else -x))
  {
    F.Case0A(x);
  }
}
