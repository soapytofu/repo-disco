module Kernel {
  export Public provides Score, SplitReady, StepReady
  export Internal reveals Score, SplitReady, StepReady
  opaque function Score(s: seq<int>, o: int): int
    decreases |s|
  { if |s| == 0 then 0 else o * s[0] + Score(s[1..], o + 1) }
  opaque predicate SplitReady(s: seq<int>, t: seq<int>, o: int) {
    |s| > 0 && |s + t| > 0 && (s+t)[0] == s[0] &&
    (s+t)[1..] == s[1..] + t && o + 1 + |s[1..]| == o + |s|
  }
  opaque predicate StepReady(s: seq<int>, t: seq<int>, o: int) {
    |s| > 0 && SplitReady(s,t,o) &&
    Score(s[1..]+t,o+1) == Score(s[1..],o+1) + Score(t,(o+1)+|s[1..]|)
  }
}
