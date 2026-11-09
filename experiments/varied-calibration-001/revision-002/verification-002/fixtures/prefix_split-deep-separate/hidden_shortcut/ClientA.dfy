include "Kernel.dfy"
include "HelperA.dfy"
module ClientA {
  import K = Kernel`Public
  import H = HelperA
  lemma Target(s: seq<int>,i: int,j: int)
    requires 0<=i<=|s| && 0<=j<=|s|-i
    ensures K.Prefix(s,i+j)==K.Prefix(s,i)+K.Prefix(s[i..],j)
    decreases i
  { H.Prove(s,i,j); }
}
