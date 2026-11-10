module Kernel {
  export Public provides Clamp, Region reveals Abs
  export Internal reveals Clamp, Region, Abs
  function Abs(x: int): int { if x<0 then -x else x }
  opaque function Clamp(l: int,h: int,x: int): int { if x<l then l else if x>h then h else x }
  opaque predicate Region(l: int,h: int,x: int,r: int) {
    l<=h && ((r==0 && x<l) || (r==1 && l<=x<=h) || (r==2 && x>h))
  }
}
