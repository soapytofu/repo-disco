include "Facts.dfy"
module ClientC {
  import F = Facts`ViewA
  lemma Extend(s: seq<int>, t: seq<int>, u: seq<int>)
    ensures F.Total(t + s + t) == F.Total(t) + F.Total(s) + F.Total(t)
  {
    F.AppendA(t, s);
  }
}
