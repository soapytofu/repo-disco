include "Facts.dfy"
module ClientC {
  import F = Facts`ViewA
  lemma Extend(s: seq<int>, t: seq<int>, u: seq<int>)
    ensures F.Total(s + t + u) == F.Total(s) + F.Total(t) + F.Total(u)
  {
  }
}
