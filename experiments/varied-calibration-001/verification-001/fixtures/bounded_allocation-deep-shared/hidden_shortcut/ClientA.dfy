include "Kernel.dfy"
include "HelperA.dfy"
module ClientA {
  import K = Kernel`Public
  import H = HelperA
  lemma Target(a: int,b: int,c: int,d: int,t: int)
    requires a<=b && c<=d && a+c<=t<=b+d
    ensures K.Feasible(a,b,c,d,t)
  { H.Prove(a,b,c,d,t); }
}
