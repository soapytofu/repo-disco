include "Kernel.dfy"
module Api {
  export Shallow provides K, Below, Within, Above
  export Deep provides K, Assemble
  import K = Kernel`Internal
  lemma Below(x: int, l: int, h: int)
    requires l <= h && x < l
    ensures K.Clamp(x,l,h) == l
  { reveal K.Clamp(); reveal K.Lower(); reveal K.Upper(); }
  lemma Within(x: int, l: int, h: int)
    requires l <= x <= h
    ensures K.Clamp(x,l,h) == x
  { reveal K.Clamp(); reveal K.Lower(); reveal K.Upper(); }
  lemma Above(x: int, l: int, h: int)
    requires l <= h && h < x
    ensures K.Clamp(x,l,h) == h
  { reveal K.Clamp(); reveal K.Lower(); reveal K.Upper(); }
  lemma Assemble(x: int, l: int, h: int, lower: int, result: int)
    requires K.Lower(x,l) == lower && K.Upper(lower,h) == result
    ensures K.Clamp(x,l,h) == result
  { reveal K.Clamp(); }
}
