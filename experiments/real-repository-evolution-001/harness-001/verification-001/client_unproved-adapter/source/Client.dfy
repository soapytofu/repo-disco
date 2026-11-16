include "Kernel.dfy"
include "Helper.dfy"
module Client {
  import K = Kernel
  import H = Helper
  method Target(m: map<int,int>, key: int) returns (remaining: map<int,int>, removed: map<int,int>)
    ensures remaining == K.Erase(m,key)
    ensures removed == K.Entry(m,key)
  {
    remaining := H.Transfer(m,key);
    removed := K.Entry(m,key);
  }
}
