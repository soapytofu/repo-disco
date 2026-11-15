include "Kernel.dfy"
module Api {
  export Public provides K, Finish
  import K = Kernel`Internal
  lemma Finish(a: int, b: int, c: int, d: int, gap: int, u: int, v: int)
    requires K.Left(a,b,u) && K.Right(c,d,v) && K.Offset(gap,u,v)
    ensures K.Feasible(a,b,c,d,gap)
  {
    reveal K.Left(); reveal K.Right(); reveal K.Offset(); reveal K.Candidate();
    assert K.Candidate(a,b,c,d,gap,u,v);
    reveal K.Feasible();
    assert exists p: int, q: int {:trigger K.Candidate(a,b,c,d,gap,p,q)} :: K.Candidate(a,b,c,d,gap,p,q);
  }
}
