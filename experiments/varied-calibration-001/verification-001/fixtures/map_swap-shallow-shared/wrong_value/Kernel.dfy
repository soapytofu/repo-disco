module Kernel {
  export Public provides Swap
  export Internal reveals Swap
  opaque function Swap(m: map<int,int>,k: int,j: int): map<int,int> {
    if k in m && j in m then m[k := m[j]][j := m[k]] else m
  }
}
