include "Kernel.dfy"
module Api {
  export Shallow provides K, Direct
  export Deep provides K, Finish
  import K = Kernel`Internal
  lemma Direct(a: int, b: int, c: int, d: int, gap: int, u: int, v: int)
    requires a <= u <= b && c <= u <= d && a <= v <= b && c <= v <= d
    requires 0 < gap && u + gap <= v
    ensures K.Room(a,b,c,d,gap)
  {
    reveal K.Room(); reveal K.Witness();
    assert K.Witness(a,b,c,d,gap,u,v);
    assert exists p: int, q: int {:trigger K.Witness(a,b,c,d,gap,p,q)} :: K.Witness(a,b,c,d,gap,p,q);
  }
  lemma Finish(a: int, b: int, c: int, d: int, gap: int, u: int, v: int)
    requires K.Joined(a,b,c,d,u) && K.Joined(a,b,c,d,v) && K.Separated(u,v,gap)
    ensures K.Room(a,b,c,d,gap)
  {
    reveal K.Joined(); reveal K.LeftFact(); reveal K.RightFact(); reveal K.Separated();
    Direct(a,b,c,d,gap,u,v);
  }
}
