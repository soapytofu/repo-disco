module Kernel {
  export Public provides Compress, Clean
  export Internal reveals Compress, Clean
  opaque function Compress(s: seq<int>): seq<int>
    decreases |s|
  {
    if |s| < 2 then s
    else if s[0] == s[1] then Compress(s[1..])
    else [s[0]] + Compress(s[1..])
  }
  opaque ghost predicate Clean(s: seq<int>)
    decreases |s|
  { |s| < 2 || (s[0] != s[1] && Clean(s[1..])) }
}
