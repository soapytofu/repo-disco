include "Kernel.dfy"
module Api {
  export Public provides K, Finish
  import K = Kernel`Internal
  lemma Finish(a: int, b: int, e: int, u: int)
    requires K.InRange(a,b,u) && u != e
    ensures K.Feasible(a,b,e)
  {
    reveal K.InRange(); reveal K.Candidate();
    assert K.Candidate(a,b,e,u);
    reveal K.Feasible();
    assert exists v: int :: K.Candidate(a,b,e,v);
  }
}
