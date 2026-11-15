module Kernel {
  export Public provides Override, Restrict, Compose
  export Internal reveals Override, Restrict, Compose
  opaque function Override(f1: map<int,int>, f2: map<int,int>): map<int,int> {
    map x | x in f1.Keys + f2.Keys :: if x in f2 then f2[x] else f1[x]
  }
  opaque function Restrict(f: map<int,int>, keep: set<int>): map<int,int> {
    map x | x in f && x in keep :: f[x]
  }
  opaque function Compose(f: map<int,int>, g: map<int,int>): map<int,int> {
    map x | x in f && f[x] in g :: g[f[x]]
  }
}
