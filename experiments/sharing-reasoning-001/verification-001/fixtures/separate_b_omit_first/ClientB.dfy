include "Facts.dfy"
module ClientB {
  import F = Facts`ViewB
  lemma Prove(s: seq<int>, t: seq<int>, u: seq<int>, k: nat)
    requires F.Size(t) > k
    ensures F.Large(s + (t + u), k)
  {
    F.ConcatB(s, t + u);
    F.Finish(s + (t + u), k);
  }
}
