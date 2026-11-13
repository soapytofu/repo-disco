module Kernel {
  export Public provides Cut
  export Internal reveals Cut
  opaque function Cut(t: int, x: int): int { if x <= t then 0 else x-t }
}
