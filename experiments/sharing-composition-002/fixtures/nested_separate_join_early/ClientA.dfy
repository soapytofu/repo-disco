include "Facts.dfy"
module ClientA {
  import F = Facts`ViewA
  lemma Prove(s: nat, t: nat, u: nat, k: nat)
    requires F.Value(s) > k
    ensures F.Large(F.Pair(F.Pair(F.Step(s), F.Step(t)), F.Step(u)), k + 3)
  {
    F.JoinA(F.Step(s), F.Step(t));
    F.LiftA(s);
    F.LiftA(t);
    F.LiftA(u);
    F.JoinA(F.Pair(F.Step(s), F.Step(t)), F.Step(u));
    F.Finish(F.Pair(F.Pair(F.Step(s), F.Step(t)), F.Step(u)), k + 3);
  }
}
