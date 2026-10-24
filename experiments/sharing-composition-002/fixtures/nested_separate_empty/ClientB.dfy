include "Facts.dfy"
module ClientB {
  import F = Facts`ViewB
  lemma Prove(s: nat, t: nat, u: nat, k: nat)
    requires F.Value(t) > k
    ensures F.Large(F.Pair(F.Pair(F.Step(t), F.Step(u)), F.Step(s)), k + 3)
  {
  }
}
