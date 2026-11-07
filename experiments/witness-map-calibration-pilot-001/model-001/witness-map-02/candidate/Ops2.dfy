include "Kernel.dfy"
module Ops2 {
  export Hidden provides K
  export Public provides K, PutAt, DropAt
  import K = Kernel`Internal
  lemma PutAt(m: map<int,int>, k: int, v: int, q: int)
    requires q in K.Put(m,k,v)
    ensures q == k ==> K.Put(m,k,v)[q] == v
    ensures q != k ==> q in m && K.Put(m,k,v)[q] == m[q]
  { reveal K.Put(); }
  lemma DropAt(m: map<int,int>, k: int, q: int)
    requires q in K.Drop(m,k)
    ensures q in m && q != k && K.Drop(m,k)[q] == m[q]
  { reveal K.Drop(); }
}
