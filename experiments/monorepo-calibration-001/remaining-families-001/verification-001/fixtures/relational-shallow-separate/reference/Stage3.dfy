include "Kernel.dfy"
module Stage3 {
  export Shallow provides K, Direct
  export Deep provides K, Finish
  import K = Kernel`Internal
  lemma Direct(x: int, y: int, z: int)
    requires 0 <= x <= y <= z
    ensures K.Safe(x, z)
  { reveal K.Safe(); }
  lemma Finish(x: int, y: int, z: int)
    requires K.Joined(x, y, z)
    ensures K.Safe(x, z)
  { reveal K.Joined(); reveal K.LeftFact(); reveal K.RightFact(); reveal K.Safe(); }
}
