module Kernel {
  export Public provides Override, Restrict
  export Internal reveals Override, Restrict
  opaque function Override(m: map<int,int>, n: map<int,int>): map<int,int> {
    map q | q in m.Keys + n.Keys :: if q in n then n[q] else m[q]
  }
  opaque function Restrict(m: map<int,int>, keep: set<int>): map<int,int> {
    map q | q in m && q in keep :: m[q]
  }
}
