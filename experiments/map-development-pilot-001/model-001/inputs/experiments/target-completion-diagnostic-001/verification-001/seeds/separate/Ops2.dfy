include "Kernel.dfy"
module Ops2 {
  export Hidden provides K
  export Public provides K, MoveKeys, MoveAt
  import K = Kernel`Internal
  lemma MoveKeys(m: map<int,int>,a: int,b: int)
    requires K.Ready(m,a,b)
    ensures K.Move(m,a,b).Keys == (m.Keys - {a}) + {b}
  { reveal K.Ready(); reveal K.Move(); }
  lemma MoveAt(m: map<int,int>,a: int,b: int,q: int)
    requires a in m && b !in m && a != b
    requires K.Ready(m,a,b)
    requires q == b || (q in m && q != a)
    ensures q in K.Move(m,a,b)
    ensures K.Move(m,a,b)[q] == (if q == b then m[a] else m[q])
  { reveal K.Move(); }
}
