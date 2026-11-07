include "Kernel.dfy"
module Ops1 {
  export Hidden provides K
  export Public provides K, Below, Within, Above
  import K = Kernel`Internal
  lemma Below(x: int, l: int, h: int)
    requires l <= h && x < l
    ensures K.Lower(x,l) == l
  { reveal K.Lower(); }
  lemma Within(x: int, l: int, h: int)
    requires l <= x <= h
    ensures K.Lower(x,l) == x
  { reveal K.Lower(); }
  lemma Above(x: int, l: int, h: int)
    requires l <= h && h < x
    ensures K.Lower(x,l) == x
  { reveal K.Lower(); }
}
