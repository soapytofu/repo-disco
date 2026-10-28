include "Kernel.dfy"
include "Stage1.dfy"
include "Stage2.dfy"
include "Stage3.dfy"
module HelperB {
  import K = Kernel`Public
  import S1 = Stage1`Public
  import S2 = Stage2`Public
  import End = Stage3`Deep
  lemma {:induction false} Prove(s: seq<int>, t: seq<int>)
    ensures K.Total(s + t) == K.Total(s) + K.Total(t)
    decreases |s|
  {
    if |s| == 0 {
      End.Base(s, t);
    } else {
      Prove(s, t);
      S1.Split(s, t);
      S2.Lift(s, t);
      End.Finish(s, t);
    }
  }
}
