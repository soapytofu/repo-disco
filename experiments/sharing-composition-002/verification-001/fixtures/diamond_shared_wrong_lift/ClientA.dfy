include "Facts.dfy"
module ClientA {
  import F = Facts`ViewA
  lemma Prove(s: nat, t: nat, u: nat, k: nat)
    requires F.Value(s) > k
    ensures F.Large(F.Pair(F.Step(s), F.Step(t)), k + 2)
  {
    F.LiftA(u);
    F.LiftA(t);
    F.JoinA(F.Step(s), F.Step(t));
    F.Finish(F.Pair(F.Step(s), F.Step(t)), k + 2);
  }
}
