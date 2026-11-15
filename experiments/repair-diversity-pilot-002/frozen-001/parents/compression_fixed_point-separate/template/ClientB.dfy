include "Kernel.dfy"
include "Invariant.dfy"
include "HelperB.dfy"
module ClientB {
  import K = Kernel`Public
  import I = Invariant`Public
  import H = HelperB
  lemma Target(u: seq<int>, v: seq<int>)
    ensures K.Compress(K.Compress(u+v)) == K.Compress(u+v)
  {
    I.OutputClean(u+v);
    H.Prove(K.Compress(u+v));
  }
}
