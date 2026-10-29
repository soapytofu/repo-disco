include "Kernel.dfy"
include "Stage1.dfy"
include "Stage2.dfy"
include "Stage3.dfy"
module HelperB {
  import K = Kernel`Public
  import S1 = Stage1`Public
  import S2 = Stage2`Public
  import End = Stage3`Deep
  lemma {:induction false} Prove(s: seq<int>, t: seq<int>, o: int)
    ensures K.Score(s+t,o) == K.Score(s,o) + K.Score(t,o+|s|)
    decreases |s|
  {
  }
}
