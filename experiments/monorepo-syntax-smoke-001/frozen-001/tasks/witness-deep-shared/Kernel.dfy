module Kernel {
  export Public provides LeftFact, RightFact, Joined, Overlap
  export Internal reveals LeftFact, RightFact, Joined, Overlap, Witness
  opaque predicate LeftFact(a: int, b: int, w: int) { a <= w <= b }
  opaque predicate RightFact(c: int, d: int, w: int) { c <= w <= d }
  opaque predicate Joined(a: int, b: int, c: int, d: int, w: int) {
    LeftFact(a,b,w) && RightFact(c,d,w)
  }
  opaque predicate Witness(a: int, b: int, c: int, d: int, w: int) { a <= w <= b && c <= w <= d }
  opaque ghost predicate Overlap(a: int, b: int, c: int, d: int) {
    exists w: int {:trigger Witness(a,b,c,d,w)} :: Witness(a,b,c,d,w)
  }
}
