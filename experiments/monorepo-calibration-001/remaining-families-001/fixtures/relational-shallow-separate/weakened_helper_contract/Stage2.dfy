include "Kernel.dfy"
module Stage2 {
  export Public provides K, Join
  import K = Kernel`Internal
  lemma Join(x: int, y: int, z: int)
    requires K.LeftFact(x, y)
    requires K.RightFact(y, z)
    ensures K.Joined(x, y, z)
  { reveal K.Joined(); }
}
