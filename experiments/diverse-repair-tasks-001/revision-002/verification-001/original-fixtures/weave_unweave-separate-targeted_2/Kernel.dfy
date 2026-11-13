module Kernel {
  export Public provides Weave, Left, Right
  export Internal reveals Weave, Left, Right
  opaque function Weave(s: seq<int>, t: seq<int>): seq<int>
    decreases |s|
  {
    if |s| == 0 || |t| == 0 then []
    else [s[0],t[0]] + Weave(s[1..],t[1..])
  }
  opaque function Left(u: seq<int>): seq<int>
    decreases |u|
  { if |u| < 2 then [] else [u[0]] + Left(u[2..]) }
  opaque function Right(u: seq<int>): seq<int>
    decreases |u|
  { if |u| < 2 then [] else [u[1]] + Right(u[2..]) }
}
