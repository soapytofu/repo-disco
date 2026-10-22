include "OrderFacts.dfy"
include "Reachability.dfy"
module Client {
  import O = OrderFacts
  import R = Reachability
  lemma Connect(a: int, b: int, c: int)
    requires O.Before(a, b) && O.Before(b, c)
    ensures R.Reach(a, c)
  {
  }
}
