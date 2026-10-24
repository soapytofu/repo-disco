module Facts {
  export ViewA provides Value, Step, Pair, Large, LiftA, JoinA, Finish
  export ViewB provides Value, Step, Pair, Large, LiftB, JoinB, Finish
  opaque function Value(x: nat): nat { x }
  opaque function Step(x: nat): nat { x + 1 }
  opaque function Pair(x: nat, y: nat): nat { x + y }
  opaque predicate Large(x: nat, k: nat) { Value(x) > k }
  lemma LiftA(x: nat)
    ensures Value(Step(x)) == Value(x) + 1
  { reveal Value(), Step(); }
  lemma JoinA(x: nat, y: nat)
    requires Value(x) > 0 && Value(y) > 0
    ensures Value(Pair(x, y)) == Value(x) + Value(y)
  { reveal Value(), Pair(); }
  lemma LiftB(x: nat)
    ensures Value(Step(x)) == Value(x) + 1
  { reveal Value(), Step(); }
  lemma JoinB(x: nat, y: nat)
    requires Value(x) > 0 && Value(y) > 0
    ensures Value(Pair(x, y)) == Value(x) + Value(y)
  { reveal Value(), Pair(); }
  lemma Finish(x: nat, k: nat)
    requires Value(x) > k
    ensures Large(x, k)
  { reveal Large(); }
}
