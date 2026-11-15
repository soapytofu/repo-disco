include "Kernel.dfy"
include "Invariant.dfy"
include "HelperA.dfy"
module ClientA {
  import K = Kernel`Public
  import I = Invariant`Public
  import H = HelperA
  lemma Target(s: seq<int>)
    ensures K.Compress(K.Compress(s)) == K.Compress(s)
  {
    I.OutputClean(s);
    H.Prove(K.Compress(s));
  }
}
