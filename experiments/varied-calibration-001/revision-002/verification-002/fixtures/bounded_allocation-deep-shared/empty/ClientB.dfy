include "Kernel.dfy"
include "HelperB.dfy"
module ClientB {
  import K = Kernel`Public
  import H = HelperB
  lemma Target(a: int,b: int,c: int,d: int,t: int,shift: int)
    requires a<=b && c<=d && a+c<=t<=b+d
    ensures K.Feasible(c+shift,d+shift,a+shift,b+shift,t+2*shift)
  { H.Prove(c+shift,d+shift,a+shift,b+shift,t+2*shift); }
}
