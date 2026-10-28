include "Kernel.dfy"
module Stage2 {
  export Public provides K, Lift
  import K = Kernel`Internal
  lemma Lift(s: seq<int>, t: seq<int>)
    requires |s| > 0
    requires K.SplitReady(s, t)
    requires K.Total(s[1..] + t) == K.Total(s[1..]) + K.Total(t)
    ensures K.StepReady(s, t)
  { reveal K.StepReady(); }
}
