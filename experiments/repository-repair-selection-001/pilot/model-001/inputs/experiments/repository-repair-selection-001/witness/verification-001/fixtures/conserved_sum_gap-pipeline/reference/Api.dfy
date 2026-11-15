include "Kernel.dfy"
module Api {
  export Bounds provides K, Balance
  export Proof provides K, Finish
  export Clients provides K, Choose
  export Hidden provides K, DirectFinish
  import K = Kernel`Internal
  lemma Balance(a: int, b: int, c: int, d: int, s: int, u: int, v: int)
    requires K.LeftFact(a,b,u) && K.RightFact(c,d,v) && K.SumFact(s,u,v)
    ensures K.Balanced(a,b,c,d,s,u,v)
  {
    reveal K.LeftFact(); reveal K.RightFact(); reveal K.SumFact(); reveal K.Balanced();
  }
  lemma Finish(a: int, b: int, c: int, d: int, s: int, g: int, u: int, v: int)
    requires K.Balanced(a,b,c,d,s,u,v) && K.GapFact(g,u,v)
    ensures K.Feasible(a,b,c,d,s,g)
  {
    reveal K.Balanced(); reveal K.GapFact(); reveal K.Valid();
    assert K.Valid(a,b,c,d,s,g,u,v);
    reveal K.Feasible();
    assert exists p: int, q: int {:trigger K.Valid(a,b,c,d,s,g,p,q)} :: K.Valid(a,b,c,d,s,g,p,q);
  }
  lemma Choose(a: int, b: int, c: int, d: int, s: int, g: int) returns (u: int, v: int)
    requires K.Feasible(a,b,c,d,s,g)
    ensures a <= u <= b && c <= v <= d
    ensures u + v == s && 0 < g && u + g <= v
  {
    reveal K.Feasible();
    u, v :| K.Valid(a,b,c,d,s,g,u,v);
    reveal K.Valid();
  }
  lemma DirectFinish(a: int, b: int, c: int, d: int, s: int, g: int, u: int, v: int)
    requires a <= u <= b && c <= v <= d && u + v == s && 0 < g && u + g <= v
    ensures K.Feasible(a,b,c,d,s,g)
  {
    reveal K.Valid(); assert K.Valid(a,b,c,d,s,g,u,v);
    reveal K.Feasible();
    assert exists p: int, q: int {:trigger K.Valid(a,b,c,d,s,g,p,q)} :: K.Valid(a,b,c,d,s,g,p,q);
  }
}
