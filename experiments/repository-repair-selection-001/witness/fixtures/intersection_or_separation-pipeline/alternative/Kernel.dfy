module Kernel {
  export Public provides LeftFact, RightFact, LeftGap, RightGap, Valid, Decided
  export Internal reveals LeftFact, RightFact, LeftGap, RightGap, Valid, Decided
  opaque predicate LeftFact(a: int, b: int, w: int) { a <= w <= b }
  opaque predicate RightFact(c: int, d: int, w: int) { c <= w <= d }
  opaque predicate LeftGap(b: int, c: int) { b < c }
  opaque predicate RightGap(d: int, a: int) { d < a }
  opaque predicate Valid(a: int, b: int, c: int, d: int, kind: int, w: int) {
    (kind == 0 && a <= w <= b && c <= w <= d) ||
    (kind == -1 && b < c) || (kind == 1 && d < a)
  }
  opaque ghost predicate Decided(a: int, b: int, c: int, d: int) {
    exists kind: int, w: int {:trigger Valid(a,b,c,d,kind,w)} :: Valid(a,b,c,d,kind,w)
  }
}
