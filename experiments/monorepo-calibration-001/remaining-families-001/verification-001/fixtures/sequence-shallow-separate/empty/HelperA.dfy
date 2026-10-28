include "Kernel.dfy"
include "Stage1.dfy"
include "Stage2.dfy"
include "Stage3.dfy"
module HelperA {
  import K = Kernel`Public
  import End = Stage3`Shallow
  lemma {:induction false} Prove(s: seq<int>, t: seq<int>)
    ensures K.Total(s + t) == K.Total(s) + K.Total(t)
    decreases |s|
  {
  }
}
