module Kernel {
  export Public provides LeftFact, RightFact, Joined, Safe
  export Internal reveals LeftFact, RightFact, Joined, Safe
  opaque predicate LeftFact(x: int, y: int) { 0 <= x <= y }
  opaque predicate RightFact(y: int, z: int) { y <= z }
  opaque predicate Joined(x: int, y: int, z: int) { LeftFact(x, y) && RightFact(y, z) }
  opaque predicate Safe(x: int, z: int) { 0 <= x <= z }
}
