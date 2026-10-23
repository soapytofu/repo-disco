include "Facts.dfy"
module ClientA {
  import F = Facts`ViewA
  lemma Prove(s: seq<int>, t: seq<int>, u: seq<int>, k: nat)
    requires F.Size(s) > k
    ensures F.Large((s + t) + u, k)
  {
    F.Finish((s + t) + u, k);
    F.ConcatA(s, t);
    F.ConcatA(s + t, u);
  }
}
