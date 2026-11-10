include "Kernel.dfy"
module Ops1 {
  export Hidden provides K
  export Public provides K, Left, Right, Balance
  import K = Kernel`Internal
  lemma Left(a: int,b: int,u: int)
    requires a<=u<=b
    ensures K.UBound(a,b,u)
  { reveal K.UBound(); }
  lemma Right(c: int,d: int,v: int)
    requires c<=v<=d
    ensures K.VBound(c,d,v)
  { reveal K.VBound(); }
  lemma Balance(t: int,u: int,v: int)
    requires u+v==t
    ensures K.Balanced(t,u,v)
  { reveal K.Balanced(); }
}
