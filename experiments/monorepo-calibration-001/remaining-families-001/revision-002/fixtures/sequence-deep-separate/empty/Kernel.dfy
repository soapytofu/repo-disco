module Kernel {
  export Public provides Total, SplitReady, StepReady
  export Internal reveals Total, SplitReady, StepReady
  opaque function Total(s: seq<int>): int
    decreases |s|
  { if |s| == 0 then 0 else s[0] + Total(s[1..]) }
  opaque predicate SplitReady(s: seq<int>, t: seq<int>) {
    |s| > 0 && |s + t| > 0 && (s + t)[0] == s[0] && (s + t)[1..] == s[1..] + t
  }
  opaque predicate StepReady(s: seq<int>, t: seq<int>) {
    |s| > 0 && SplitReady(s, t) && Total(s[1..] + t) == Total(s[1..]) + Total(t)
  }
}
