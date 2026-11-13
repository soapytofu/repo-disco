include "Kernel.dfy"
module Api {
  export Public provides K, Finish
  import K = Kernel`Internal
  lemma Finish(a: int, b: int, e: int, u: int)
    requires K.InRange(a,b,u) && u != e
    ensures K.Feasible(a,b,e)
  {
    reveal K.InRange(); reveal K.Feasible();
    assert a <= u <= b && u != e;
  }
}
