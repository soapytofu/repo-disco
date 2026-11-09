module Kernel {
  export Public provides Prefix, StepFact
  export Internal reveals Total, Prefix, StepFact
  opaque function Total(s: seq<int>): int
    decreases |s|
  { if |s|==0 then 0 else s[0]+Total(s[1..]) }
  opaque function Prefix(s: seq<int>,n: int): int
    requires 0<=n<=|s|
  { Total(s[..n]) }
  opaque predicate StepFact(s: seq<int>,n: int)
    requires 0<=n<=|s|
  { if n==0 then Prefix(s,n)==0 else Prefix(s,n)==s[0]+Prefix(s[1..],n-1) }
}
