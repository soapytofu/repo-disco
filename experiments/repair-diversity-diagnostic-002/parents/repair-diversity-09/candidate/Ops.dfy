include "Kernel.dfy"
module Ops {
  export Public provides K, Low, High
  export Internal provides K, Low, High, Range
  import K = Kernel`Internal
  lemma Low(c: int, x: int, y: int)
    requires 0 <= c && 0 <= x && 0 <= y && x+y <= c
    ensures K.Sat(c,x,y) == x+y
  { reveal K.Sat(); }
  lemma High(c: int, x: int, y: int)
    requires 0 <= c && 0 <= x && 0 <= y && c <= x+y
    ensures K.Sat(c,x,y) == c
  { reveal K.Sat(); }
  lemma Range(c: int, x: int, y: int)
    requires 0 <= c && 0 <= x && 0 <= y
    ensures 0 <= K.Sat(c,x,y) <= c
  { reveal K.Sat(); }
}
