include "Kernel.dfy"
module Ops {
  export Public provides K, PutKeys, PutAt, ExchangeShape
  export Hidden provides K, HiddenPutAt
  import K = Kernel`Internal
  lemma PutKeys(m: map<int,int>, key: int, value: int)
    ensures K.Put(m,key,value).Keys == m.Keys + {key}
  { reveal K.Put(); }
  lemma PutAt(m: map<int,int>, key: int, value: int, x: int)
    requires x in m || x == key
    ensures x in K.Put(m,key,value)
    ensures K.Put(m,key,value)[x] == (if x == key then value else m[x])
  { reveal K.Put(); }
  lemma ExchangeShape(m: map<int,int>, p: int, q: int)
    requires p in m && q in m
    ensures K.Exchange(m,p,q) == K.Put(K.Put(m,p,m[q]),q,m[p])
  { reveal K.Exchange(); }
  lemma HiddenPutAt(m: map<int,int>, key: int, value: int, x: int)
    requires x in m || x == key
    ensures x in K.Put(m,key,value)
    ensures K.Put(m,key,value)[x] == (if x == key then value else m[x])
  { reveal K.Put(); }
}
