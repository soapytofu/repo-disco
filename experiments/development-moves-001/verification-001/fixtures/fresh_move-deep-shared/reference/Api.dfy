include "Kernel.dfy"
module Api {
  export Shallow provides K, ObserveMove, Equal
  export Deep provides K, Equal
  import K = Kernel`Internal
  lemma ObserveMove(m: map<int,int>,a: int,b: int)
    requires a in m && b !in m && a != b
    ensures K.Move(m,a,b).Keys == (m.Keys - {a}) + {b}
    ensures forall q :: q in K.Move(m,a,b) ==>
      K.Move(m,a,b)[q] == (if q == b then m[a] else m[q])
  { reveal K.Move(); }
  lemma Equal(left: map<int,int>,right: map<int,int>)
    requires left.Keys == right.Keys
    requires forall q :: q in left ==> q in right && left[q] == right[q]
    ensures left == right
  { }
}
