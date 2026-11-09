include "Kernel.dfy"
module Api {
  export Shallow provides K, Direct
  export Deep provides K, Finish
  import K = Kernel`Internal
  lemma Direct(a: int,b: int,c: int,d: int,t: int,u: int,v: int)
    requires a<=u<=b && c<=v<=d && u+v==t
    ensures K.Feasible(a,b,c,d,t)
  {
    reveal K.Feasible(); reveal K.Witness();
    assert K.Witness(a,b,c,d,t,u,v);
    assert exists p: int,q: int {:trigger K.Witness(a,b,c,d,t,p,q)} :: K.Witness(a,b,c,d,t,p,q);
  }
  lemma Finish(a: int,b: int,c: int,d: int,t: int,u: int,v: int)
    requires K.Bounds(a,b,c,d,u,v) && K.Balanced(t,u,v)
    ensures K.Feasible(a,b,c,d,t)
  {
    reveal K.Bounds(); reveal K.UBound(); reveal K.VBound(); reveal K.Balanced();
    Direct(a,b,c,d,t,u,v);
  }
}
