include "Kernel.dfy"
include "Stage1.dfy"
include "Stage2.dfy"
include "Stage3.dfy"
module HelperB {
  import K = Kernel`Public
  import End = Stage3`Shallow
  lemma {:induction false} Prove(s: seq<int>, t: seq<int>, o: int)
    ensures K.Score(s+t,o) == K.Score(s,o) + K.Score(t,o+|s|)
    decreases |s|
  {
    if |s| == 0 {
      End.Base(s,t,o);
    } else {
      Prove(s,t,o+1);
      End.Direct(s,t,o);
    }
  }
}
