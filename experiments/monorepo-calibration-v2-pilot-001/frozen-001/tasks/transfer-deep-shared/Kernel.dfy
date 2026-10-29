module Kernel {
  export Public reveals Move provides Valid, Transfer, Debited, Credited
  export Internal reveals Move, Valid, Transfer, Debited, Credited
  function Move(m: map<int,int>, k: int, j: int, v: int): map<int,int>
    requires k in m && j in m
  { if k == j then m else m[k := m[k] - v][j := m[j] + v] }
  opaque predicate Valid(m: map<int,int>) { forall q :: q in m ==> m[q] >= 0 }
  opaque predicate Transfer(m: map<int,int>, n: map<int,int>, k: int, j: int, v: int)
    requires k in m && j in m
  {
    n.Keys == m.Keys && k in n && j in n &&
    n[k] + n[j] == m[k] + m[j] &&
    (if k == j then n == m else n[k] == m[k] - v && n[j] == m[j] + v) &&
    (forall q :: q in m && q != k && q != j ==> q in n && n[q] == m[q])
  }
  opaque predicate Debited(m: map<int,int>, k: int, j: int, v: int)
    requires k in m && j in m
  { k != j && 0 <= v <= m[k] && Valid(m) && Valid(m[k := m[k] - v]) }
  opaque predicate Credited(m: map<int,int>, k: int, j: int, v: int)
    requires k in m && j in m
  { Valid(Move(m,k,j,v)) && Transfer(m,Move(m,k,j,v),k,j,v) }
}
