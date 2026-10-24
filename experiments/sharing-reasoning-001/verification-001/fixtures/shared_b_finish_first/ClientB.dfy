include "Facts.dfy"
module ClientB {
  import F = Facts`ViewA
  lemma Prove(s: seq<int>, t: seq<int>, u: seq<int>, k: nat)
    requires F.Size(t) > k
    ensures F.Large(s + (t + u), k)
  {
    F.Finish(s + (t + u), k);
    F.ConcatA(t, u);
    F.ConcatA(s, t + u);
  }
}
