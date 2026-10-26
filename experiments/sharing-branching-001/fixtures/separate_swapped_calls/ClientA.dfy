include "Facts.dfy"
module ClientA {
  import F = Facts`ViewA
  lemma Prove(x: int, y: int)
    ensures F.Good(F.Wrap(if x >= 0 then x else -x))
  {
    if x >= 0 {
      F.Case1A(x);
    } else {
      F.Case0A(x);
    }
  }
}
