include "Kernel.dfy"
module Stage2 {
  export Public provides K, Lift
  import K = Kernel`Internal
  lemma Lift(s: seq<int>, t: seq<int>, o: int)
    requires |s| > 0 && K.SplitReady(s,t,o)
    requires K.Score(s[1..]+t,o+1) == K.Score(s[1..],o+1) + K.Score(t,(o+1)+|s[1..]|)
    ensures K.StepReady(s,t,o)
  { reveal K.StepReady(); }
}
