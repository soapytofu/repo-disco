module Kernel {
  export Public provides InRange, Feasible
  export Internal reveals InRange, Feasible
  opaque predicate InRange(a: int, b: int, u: int) { a <= u <= b }
  opaque predicate Feasible(a: int, b: int, e: int) {
    exists u: int :: a <= u <= b && u != e
  }
}
