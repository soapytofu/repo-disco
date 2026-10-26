include "Facts.dfy"
module ClientB {
  import F = Facts`ViewB
  lemma SumThree(s: seq<int>, t: seq<int>, u: seq<int>)
    ensures F.Total((s + t) + u) == F.Total(s) + F.Total(t) + F.Total(u)
  {
    F.AppendB(s, t);
    F.AppendB(s + t, u);
  }
}
