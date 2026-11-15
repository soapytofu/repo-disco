include "Kernel.dfy"
module Helper {
  import K = Kernel
  method Transfer(m: map<int,int>, key: int) returns (r: map<int,int>)
    requires key in m
    ensures r == K.Entry(m,key)
    ensures r.Keys == {key}
  {
    r := K.Erase(m,key);
  }
}
