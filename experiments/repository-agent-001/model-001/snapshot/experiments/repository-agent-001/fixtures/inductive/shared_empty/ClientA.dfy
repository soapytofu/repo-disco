include "Facts.dfy"
module ClientA {
  import F = Facts`ViewA
  lemma SumTwo(s: seq<int>, t: seq<int>)
    ensures F.Total(s + t) == F.Total(s) + F.Total(t)
  { F.AppendA(s, t); }
}
