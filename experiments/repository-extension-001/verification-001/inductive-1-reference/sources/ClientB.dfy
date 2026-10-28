include "Facts.dfy"
module ClientB {
  import F = Facts`ViewA
  lemma SumThree(s: seq<int>, t: seq<int>, u: seq<int>)
    ensures F.Total((s + t) + u) == F.Total(s) + F.Total(t) + F.Total(u)
  {
    F.AppendA(s, t);
    F.AppendA(s + t, u);
  }
}
