include "Kernel.dfy"
module Ops2 {
  export Public provides K, Upper
  import K = Kernel`Internal
  lemma Upper(x: int, h: int)
    ensures K.Upper(x,h) == (if x > h then h else x)
  { reveal K.Upper(); }
}
