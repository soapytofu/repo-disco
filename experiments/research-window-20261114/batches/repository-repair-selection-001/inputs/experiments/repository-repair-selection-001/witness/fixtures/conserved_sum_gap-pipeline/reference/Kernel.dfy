module Kernel {
  export Public provides LeftFact, RightFact, SumFact, Balanced, GapFact, Valid, Feasible
  export Internal reveals LeftFact, RightFact, SumFact, Balanced, GapFact, Valid, Feasible
  opaque predicate LeftFact(a: int, b: int, u: int) { a <= u <= b }
  opaque predicate RightFact(c: int, d: int, v: int) { c <= v <= d }
  opaque predicate SumFact(s: int, u: int, v: int) { u + v == s }
  opaque predicate Balanced(a: int, b: int, c: int, d: int, s: int, u: int, v: int) {
    a <= u <= b && c <= v <= d && u + v == s
  }
  opaque predicate GapFact(g: int, u: int, v: int) { 0 < g && u + g <= v }
  opaque predicate Valid(a: int, b: int, c: int, d: int, s: int, g: int, u: int, v: int) {
    a <= u <= b && c <= v <= d && u + v == s && 0 < g && u + g <= v
  }
  opaque ghost predicate Feasible(a: int, b: int, c: int, d: int, s: int, g: int) {
    exists u: int, v: int {:trigger Valid(a,b,c,d,s,g,u,v)} :: Valid(a,b,c,d,s,g,u,v)
  }
}
