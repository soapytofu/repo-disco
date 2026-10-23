include "OrderFacts.dfy"
module Reachability {
  import O = OrderFacts
  export provides O, Reach, Lift
  opaque predicate Reach(a: int, b: int) { O.Before(a, b) }

  lemma Lift(a: int, b: int)
    requires O.Before(a, b)
    ensures Reach(a, b)
  { reveal Reach(); }
}
