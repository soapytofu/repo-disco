module Kernel {
  export Public provides Sat
  export Internal reveals Sat
  opaque function Sat(c: int, x: int, y: int): int
  { if x+y <= c then x+y else c }
}
