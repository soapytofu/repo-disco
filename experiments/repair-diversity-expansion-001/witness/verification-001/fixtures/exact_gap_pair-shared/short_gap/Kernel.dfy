module Kernel {
  export Public provides Left, Right, Offset, Feasible
  export Internal reveals Left, Right, Offset, Candidate, Feasible
  opaque predicate Left(a: int, b: int, u: int) { a <= u <= b }
  opaque predicate Right(c: int, d: int, v: int) { c <= v <= d }
  opaque predicate Offset(gap: int, u: int, v: int) { 0 < gap && v == u + gap }
  opaque predicate Candidate(a: int, b: int, c: int, d: int, gap: int, u: int, v: int) {
    a <= u <= b && c <= v <= d && 0 < gap && v == u + gap
  }
  opaque ghost predicate Feasible(a: int, b: int, c: int, d: int, gap: int) {
    exists u: int, v: int {:trigger Candidate(a,b,c,d,gap,u,v)} :: Candidate(a,b,c,d,gap,u,v)
  }
}
