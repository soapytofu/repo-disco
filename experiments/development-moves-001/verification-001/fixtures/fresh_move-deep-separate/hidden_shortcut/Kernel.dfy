module Kernel {
  export Public provides Move, Ready
  export Internal reveals Move, Ready
  opaque predicate Ready(m: map<int,int>,a: int,b: int) {
    a in m && b !in m && a != b
  }
  opaque function Move(m: map<int,int>,a: int,b: int): map<int,int> {
    if a in m && b !in m && a != b then
      (map q | q in m && q != a :: m[q])[b := m[a]]
    else m
  }
}
