include "Kernel.dfy"
module Api {
  export Shallow provides K, Observe
  export Deep provides K, Assemble
  import K = Kernel`Internal
  lemma Observe(x: int, l: int, h: int)
    requires l <= h
    ensures K.Clamp(x,l,h) == (if x < l then l else if x > h then h else x)
  { reveal K.Clamp(); reveal K.Lower(); reveal K.Upper(); }
  lemma Assemble(x: int, l: int, h: int, u: int, v: int)
    requires l <= h && u == K.Lower(x,l) && v == K.Upper(u,h)
    ensures K.Clamp(x,l,h) == v
  { reveal K.Clamp(); }
}
