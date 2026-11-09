include "Kernel.dfy"
module Ops1 {
  export Hidden provides K
  export Public provides K, Below, Within, Above
  import K = Kernel`Internal
  lemma Below(l: int,h: int,x: int)
    requires l<=h && x<l
    ensures K.Region(l,h,x,0)
  { reveal K.Region(); }
  lemma Within(l: int,h: int,x: int)
    requires l<=x<=h
    ensures K.Region(l,h,x,1)
  { reveal K.Region(); }
  lemma Above(l: int,h: int,x: int)
    requires l<=h && x>h
    ensures K.Region(l,h,x,2)
  { reveal K.Region(); }
}
