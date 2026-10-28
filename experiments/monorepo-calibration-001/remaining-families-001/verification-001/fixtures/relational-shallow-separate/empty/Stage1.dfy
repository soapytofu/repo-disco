include "Kernel.dfy"
module Stage1 {
  export Public provides K, Left, Right
  import K = Kernel`Internal
  lemma Left(x: int, y: int)
    requires 0 <= x <= y
    ensures K.LeftFact(x, y)
  { reveal K.LeftFact(); }
  lemma Right(y: int, z: int)
    requires y <= z
    ensures K.RightFact(y, z)
  { reveal K.RightFact(); }
}
