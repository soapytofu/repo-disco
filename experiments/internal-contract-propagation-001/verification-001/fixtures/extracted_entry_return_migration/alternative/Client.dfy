include "Kernel.dfy"
include "Helper.dfy"
module Client {
  import K = Kernel
  import H = Helper
  method Target(m: map<int,int>, key: int) returns (remaining: map<int,int>, removed: map<int,int>)
    ensures remaining == K.Erase(m,key)
    ensures removed == K.Entry(m,key)
  {
    if key !in m {
      removed := map[];
      remaining := m;
    } else {
      var patch := H.Transfer(m,key);
      var keep := m.Keys - patch.Keys;
      remaining := map x | x in keep :: m[x];
      removed := patch;
      assert remaining.Keys == K.Erase(m,key).Keys;
      assert forall x | x in remaining :: remaining[x] == K.Erase(m,key)[x];
      assert remaining == K.Erase(m,key);
    }
  }
}
