include "Kernel.dfy"
include "HelperB.dfy"
module ClientB {
  import K = Kernel`Public
  import H = HelperB
  lemma Target(m: map<int,int>,a: int,b: int,c: int,q: int)
    requires a in m && b !in m && c !in m
    requires a != b && b != c && a != c
    requires q in K.Move(m,a,c)
    ensures q in K.Move(K.Move(m,a,b),b,c)
    ensures K.Move(K.Move(m,a,b),b,c)[q] == K.Move(m,a,c)[q]
  { H.Prove(m,a,b,c); }
}
