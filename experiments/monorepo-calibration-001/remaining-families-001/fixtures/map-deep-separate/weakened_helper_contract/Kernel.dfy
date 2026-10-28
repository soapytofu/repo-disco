module Kernel {
  export Public provides Valid, Values, Frame, Ready, FrameTwo
  export Internal reveals Valid, Values, Frame, Ready, FrameTwo
  opaque predicate Valid(m: map<int, int>) { forall q :: q in m ==> m[q] >= 0 }
  opaque predicate Values(m: map<int, int>) { forall q :: q in m ==> m[q] >= 0 }
  opaque predicate Frame(m: map<int, int>, n: map<int, int>, k: int) {
    forall q :: q in m && q != k ==> q in n && n[q] == m[q]
  }
  opaque predicate Ready(m: map<int, int>, k: int, v: int) {
    Values(m[k := v]) && Frame(m, m[k := v], k)
  }
  opaque predicate FrameTwo(m: map<int, int>, n: map<int, int>, k: int, j: int) {
    forall q :: q in m && q != k && q != j ==> q in n && n[q] == m[q]
  }
}
