include "Kernel.dfy"
module Stage2 {
  export Public provides K, Advance
  import K = Kernel`Internal
  lemma Advance(x: int, y: int)
    requires K.Ready1(x, y)
    requires y >= x
    ensures K.Ready2(x, y)
  { reveal K.Ready1(); reveal K.Ready2(); }
}
