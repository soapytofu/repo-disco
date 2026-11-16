include "Kernel.dfy"
include "Helper.dfy"
module Client {
  import K = Kernel
  import H = Helper
  method Target(m: map<int,int>, key: int) returns (remaining: map<int,int>, removed: map<int,int>)
    ensures remaining == K.Erase(m,key)
    ensures removed == K.Entry(m,key)
  {
    if key in m {
      removed := H.Unknown(m,key);
      remaining := K.Exclude(m,removed);
      assert removed == K.Entry(m,key);
      assert remaining.Keys == K.Erase(m,key).Keys;
      assert forall x | x in remaining :: remaining[x] == K.Erase(m,key)[x];
      assert remaining == K.Erase(m,key);
    } else {
      remaining := m;
      removed := map[];
    }
  }
}
