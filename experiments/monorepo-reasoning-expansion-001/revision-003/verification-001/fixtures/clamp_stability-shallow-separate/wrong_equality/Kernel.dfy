module Kernel {
  export Public provides Lower, Upper, Clamp
  export Internal reveals Lower, Upper, Clamp
  opaque function Lower(x: int, l: int): int { if x < l then l else x }
  opaque function Upper(x: int, h: int): int { if x > h then h else x }
  opaque function Clamp(x: int, l: int, h: int): int
    requires l <= h
  { Upper(Lower(x,l),h) }
}
