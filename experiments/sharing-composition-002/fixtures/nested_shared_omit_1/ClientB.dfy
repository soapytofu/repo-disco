include "Facts.dfy"
module ClientB {
  import F = Facts`ViewA
  lemma Prove(s: nat, t: nat, u: nat, k: nat)
    requires F.Value(t) > k
    ensures F.Large(F.Pair(F.Pair(F.Step(t), F.Step(u)), F.Step(s)), k + 3)
  {
    F.LiftA(u);
    F.JoinA(F.Step(t), F.Step(u));
    F.LiftA(s);
    F.JoinA(F.Pair(F.Step(t), F.Step(u)), F.Step(s));
    F.Finish(F.Pair(F.Pair(F.Step(t), F.Step(u)), F.Step(s)), k + 3);
  }
}
