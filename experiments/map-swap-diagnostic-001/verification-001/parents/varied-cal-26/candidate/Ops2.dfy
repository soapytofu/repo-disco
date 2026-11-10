include "Kernel.dfy"
module Ops2 {
  export Hidden provides K
  export Public provides K, ReadBelow, ReadWithin, ReadAbove
  import K = Kernel`Internal
  lemma ReadBelow(l: int,h: int,x: int)
    requires K.Region(l,h,x,0)
    ensures K.Clamp(l,h,x)==l
  { reveal K.Region(); reveal K.Clamp(); }
  lemma ReadWithin(l: int,h: int,x: int)
    requires K.Region(l,h,x,1)
    ensures K.Clamp(l,h,x)==x
  { reveal K.Region(); reveal K.Clamp(); }
  lemma ReadAbove(l: int,h: int,x: int)
    requires K.Region(l,h,x,2)
    ensures K.Clamp(l,h,x)==h
  { reveal K.Region(); reveal K.Clamp(); }
}
