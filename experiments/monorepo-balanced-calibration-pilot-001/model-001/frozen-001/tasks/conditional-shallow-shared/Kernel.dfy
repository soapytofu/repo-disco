module Kernel {
  export Public provides Encode, Safe, Ready1, Ready2 reveals Abs
  export Internal reveals Encode, Safe, Ready1, Ready2, Abs
  function Abs(x: int): int { if x >= 0 then x else -x }
  opaque function Encode(x: int, y: int): int { y - x }
  opaque predicate Safe(z: int) { z >= 0 }
  opaque predicate Ready1(x: int, y: int) { x >= 0 }
  opaque predicate Ready2(x: int, y: int) { x >= 0 && y >= x }
}
