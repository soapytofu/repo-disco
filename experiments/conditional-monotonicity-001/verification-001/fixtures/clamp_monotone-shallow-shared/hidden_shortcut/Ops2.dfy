include "Kernel.dfy"
module Ops2 {
  export Hidden provides K
  export Public provides K, Below, Within, Above
  import K = Kernel`Internal
  lemma Below(l: int, h: int)
    requires l <= h
    ensures K.Upper(l,h) == l
  { reveal K.Upper(); }
  lemma Within(x: int, l: int, h: int)
    requires l <= x <= h
    ensures K.Upper(x,h) == x
  { reveal K.Upper(); }
  lemma Above(x: int, h: int)
    requires h < x
    ensures K.Upper(x,h) == h
  { reveal K.Upper(); }
}
