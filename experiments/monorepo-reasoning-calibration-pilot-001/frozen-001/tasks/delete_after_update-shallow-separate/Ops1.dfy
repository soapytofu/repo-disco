include "Kernel.dfy"
module Ops1 {
  export Public provides K, PutKeys, DropKeys
  import K = Kernel`Internal
  lemma PutKeys(m: map<int,int>, k: int, v: int)
    ensures K.Put(m,k,v).Keys == m.Keys + {k}
  { reveal K.Put(); }
  lemma DropKeys(m: map<int,int>, k: int)
    ensures K.Drop(m,k).Keys == m.Keys - {k}
  { reveal K.Drop(); }
}
