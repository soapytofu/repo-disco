include "Kernel.dfy"
include "Ops1.dfy"
include "Ops2.dfy"
include "Api.dfy"
module HelperA {
  import K = Kernel`Public
  import A = Api`Shallow
  lemma {:induction false} Prove(s: seq<int>, t: seq<int>)
    ensures K.Rev(s+t) == K.Rev(t)+K.Rev(s)
    decreases |s|
  {
  }
}
