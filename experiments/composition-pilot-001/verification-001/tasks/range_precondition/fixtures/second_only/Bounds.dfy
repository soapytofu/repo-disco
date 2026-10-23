module Bounds {
  export provides Ready, MakeReady, ExposeReady
  opaque predicate Ready(x: int) { 0 <= x <= 10 }

  lemma MakeReady(x: int)
    requires 0 <= x <= 10
    ensures Ready(x)
  { reveal Ready(); }

  lemma ExposeReady(x: int)
    requires Ready(x)
    ensures 0 <= x <= 10
  { reveal Ready(); }
}
