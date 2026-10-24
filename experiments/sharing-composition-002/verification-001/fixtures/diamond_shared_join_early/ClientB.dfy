include "Facts.dfy"
module ClientB {
  import F = Facts`ViewA
  lemma Prove(s: nat, t: nat, u: nat, k: nat)
    requires F.Value(t) > k
    ensures F.Large(F.Pair(F.Step(t), F.Step(u)), k + 2)
  {
    F.JoinA(F.Step(t), F.Step(u));
    F.LiftA(t);
    F.LiftA(u);
    F.Finish(F.Pair(F.Step(t), F.Step(u)), k + 2);
  }
}
