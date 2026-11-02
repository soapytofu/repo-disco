module Kernel {
  export Public provides Select, Filter
  export Internal reveals Select, Filter
  opaque function Select(x: int, p: int, tail: seq<int>): seq<int>
  { if x <= p then [x]+tail else tail }
  opaque function Filter(s: seq<int>, p: int): seq<int>
    decreases |s|
  { if |s| == 0 then [] else Select(s[0],p,Filter(s[1..],p)) }
}
