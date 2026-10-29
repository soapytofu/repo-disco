include "Kernel.dfy"
module Stage3 {
  export Shallow provides K, Direct
  export Deep provides K, Finish
  import K = Kernel`Internal
  lemma Direct(a: int, b: int, c: int, d: int, w: int)
    requires a <= w <= b && c <= w <= d
    ensures K.Overlap(a,b,c,d)
  { reveal K.Overlap(); reveal K.Witness(); assert K.Witness(a,b,c,d,w);
    assert exists q: int {:trigger K.Witness(a,b,c,d,q)} :: K.Witness(a,b,c,d,q); }
  lemma Finish(a: int, b: int, c: int, d: int, w: int)
    requires K.Joined(a,b,c,d,w)
    ensures K.Overlap(a,b,c,d)
  {
    reveal K.Joined(); reveal K.LeftFact(); reveal K.RightFact(); reveal K.Overlap();
    assert a <= w <= b && c <= w <= d;
    reveal K.Witness(); assert K.Witness(a,b,c,d,w);
    assert exists q: int {:trigger K.Witness(a,b,c,d,q)} :: K.Witness(a,b,c,d,q);
  }
}
