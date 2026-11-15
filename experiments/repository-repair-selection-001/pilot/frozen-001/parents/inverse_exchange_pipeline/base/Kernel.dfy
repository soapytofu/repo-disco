module Kernel {
  export Public provides Put, Exchange reveals Inverse
  export Internal reveals Put, Exchange, Inverse
  opaque function Put(m: map<int,int>, key: int, value: int): map<int,int> {
    m[key := value]
  }
  opaque function Exchange(m: map<int,int>, p: int, q: int): map<int,int>
    requires p in m && q in m
  {
    Put(Put(m,p,m[q]),q,m[p])
  }
  predicate Inverse(m: map<int,int>, n: map<int,int>) {
    (forall x :: x in m ==> m[x] in n && n[m[x]] == x) &&
    (forall y :: y in n ==> n[y] in m && m[n[y]] == y)
  }
}
