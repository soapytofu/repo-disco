include "Kernel.dfy"
module Stage3 {
  export Shallow provides K, Direct
  export Deep provides K, Finish
  import K = Kernel`Internal
  lemma Direct(x: int, y: int)
    requires x >= 0 && y >= x
    ensures K.Safe(K.Encode(x, y))
  { reveal K.Ready2(); reveal K.Safe(); reveal K.Encode(); }
  lemma Finish(x: int, y: int)
    requires K.Ready2(x, y)
    ensures K.Safe(K.Encode(x, y))
  { reveal K.Ready2(); reveal K.Safe(); reveal K.Encode(); }
}
