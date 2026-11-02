module Kernel {
  export Public provides Put, Drop
  export Internal reveals Put, Drop
  opaque function Put(m: map<int,int>, k: int, v: int): map<int,int> { m[k := v] }
  opaque function Drop(m: map<int,int>, k: int): map<int,int>
  { map q | q in m && q != k :: m[q] }
}
