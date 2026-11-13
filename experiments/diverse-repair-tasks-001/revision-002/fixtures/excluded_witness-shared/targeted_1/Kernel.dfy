module Kernel {
  export Public provides InRange, Feasible
  export Internal reveals InRange, Feasible, Candidate
  opaque predicate InRange(a: int, b: int, u: int) { a <= u <= b }
  opaque predicate Candidate(a: int, b: int, e: int, u: int) { a <= u <= b && u != e }
  opaque predicate Feasible(a: int, b: int, e: int) {
    exists u: int :: Candidate(a,b,e,u)
  }
}
