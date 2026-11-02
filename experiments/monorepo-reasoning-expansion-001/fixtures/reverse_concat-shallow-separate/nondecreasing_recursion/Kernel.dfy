module Kernel {
  export Public provides Snoc, Rev
  export Internal reveals Snoc, Rev
  opaque function Snoc(s: seq<int>, x: int): seq<int> { s + [x] }
  opaque function Rev(s: seq<int>): seq<int>
    decreases |s|
  { if |s| == 0 then [] else Snoc(Rev(s[1..]),s[0]) }
}
