module Kernel {
  export Public provides LeftFact, RightFact, Joined, Separated, Room
  export Internal reveals LeftFact, RightFact, Joined, Separated, Room, Witness
  opaque predicate LeftFact(a: int, b: int, w: int) { a <= w <= b }
  opaque predicate RightFact(c: int, d: int, w: int) { c <= w <= d }
  opaque predicate Joined(a: int, b: int, c: int, d: int, w: int) { LeftFact(a,b,w) && RightFact(c,d,w) }
  opaque predicate Separated(u: int, v: int, gap: int) { 0 < gap && u + gap <= v }
  opaque predicate Witness(a: int, b: int, c: int, d: int, gap: int, u: int, v: int) {
    a <= u <= b && c <= u <= d && a <= v <= b && c <= v <= d && 0 < gap && u + gap <= v
  }
  opaque ghost predicate Room(a: int, b: int, c: int, d: int, gap: int) {
    exists u: int, v: int {:trigger Witness(a,b,c,d,gap,u,v)} :: Witness(a,b,c,d,gap,u,v)
  }
}
