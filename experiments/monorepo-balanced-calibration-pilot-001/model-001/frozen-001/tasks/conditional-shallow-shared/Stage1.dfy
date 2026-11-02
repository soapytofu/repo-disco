include "Kernel.dfy"
module Stage1 {
  export Public provides K, Start
  import K = Kernel`Internal
  lemma Start(x: int, y: int)
    requires x >= 0
    ensures K.Ready1(x, y)
  { reveal K.Ready1(); }
}
