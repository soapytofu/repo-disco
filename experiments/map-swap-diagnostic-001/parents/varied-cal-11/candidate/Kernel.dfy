module Kernel {
  export Public provides UBound, VBound, Bounds, Balanced, Feasible
  export Internal reveals UBound, VBound, Bounds, Balanced, Witness, Feasible
  opaque predicate UBound(a: int,b: int,u: int) { a <= u <= b }
  opaque predicate VBound(c: int,d: int,v: int) { c <= v <= d }
  opaque predicate Bounds(a: int,b: int,c: int,d: int,u: int,v: int) { UBound(a,b,u) && VBound(c,d,v) }
  opaque predicate Balanced(t: int,u: int,v: int) { u+v == t }
  opaque predicate Witness(a: int,b: int,c: int,d: int,t: int,u: int,v: int) { a<=u<=b && c<=v<=d && u+v==t }
  opaque ghost predicate Feasible(a: int,b: int,c: int,d: int,t: int) {
    exists u: int,v: int {:trigger Witness(a,b,c,d,t,u,v)} :: Witness(a,b,c,d,t,u,v)
  }
}
