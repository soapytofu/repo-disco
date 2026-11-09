module Kernel {
  export Public provides Swap, Domain
  export Internal reveals Swap, Domain
  opaque predicate Domain(m: map<int,int>,k: int,j: int) { k in m && j in m }
  opaque function Swap(m: map<int,int>,k: int,j: int): map<int,int> {
    if k in m && j in m then m[k := m[j]][j := m[k]] else m
  }
}
