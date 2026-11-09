include "Kernel.dfy"
module Api {
  export Shallow provides K, Below, Within, Above
  export Deep provides K
  import K = Kernel`Internal
  lemma Below(l: int,h: int,x: int)
    requires l<=h && x<l
    ensures K.Clamp(l,h,x)==l
  { reveal K.Clamp(); }
  lemma Within(l: int,h: int,x: int)
    requires l<=x<=h
    ensures K.Clamp(l,h,x)==x
  { reveal K.Clamp(); }
  lemma Above(l: int,h: int,x: int)
    requires l<=h && x>h
    ensures K.Clamp(l,h,x)==h
  { reveal K.Clamp(); }
}
