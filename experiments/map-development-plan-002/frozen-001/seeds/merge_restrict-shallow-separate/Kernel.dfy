module Kernel {
  export Public provides Separate, Merge, Restrict
  export Internal reveals Separate, Merge, Restrict
  opaque predicate Separate(m: map<int,int>,n: map<int,int>) {
    forall q :: q in m ==> q !in n
  }
  opaque function Merge(m: map<int,int>,n: map<int,int>): map<int,int> {
    if Separate(m,n) then
      map q | q in m.Keys + n.Keys :: if q in m then m[q] else n[q]
    else map[]
  }
  opaque function Restrict(m: map<int,int>,keep: set<int>): map<int,int> {
    map q | q in m && q in keep :: m[q]
  }
}
