include "Facts.dfy"
module ClientA {
  import F = Facts`ViewA
  lemma Prove(s: nat, t: nat, u: nat, k: nat)
    requires F.Value(s) > k
    ensures F.Large(F.Pair(F.Step(s), F.Step(t)), k + 2)
  {
  }
}
