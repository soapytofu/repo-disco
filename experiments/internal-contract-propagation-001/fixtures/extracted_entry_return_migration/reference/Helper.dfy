include "Kernel.dfy"
module Helper {
  import K = Kernel
  method Transfer(m: map<int,int>, key: int) returns (r: map<int,int>)
    ensures r == K.Erase(m,key)
  {
    r := K.Erase(m,key);
  }
}
