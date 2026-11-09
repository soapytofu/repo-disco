include "Kernel.dfy"
include "HelperB.dfy"
module ClientB {
  import K = Kernel`Public
  import H = HelperB
  lemma Target(s: seq<int>,k: int)
    requires 0<=k<=|s|
    ensures K.Prefix(s,|s|)==K.Prefix(s,k)+K.Prefix(s[k..],|s|-k)
  { H.Prove(s,k,|s|-k); }
}
