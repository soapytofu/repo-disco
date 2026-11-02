include "Kernel.dfy"
module Ops1 {
  export Public provides K, Lower
  import K = Kernel`Internal
  lemma Lower(x: int, l: int)
    ensures K.Lower(x,l) == (if x < l then l else x)
  { reveal K.Lower(); }
}
