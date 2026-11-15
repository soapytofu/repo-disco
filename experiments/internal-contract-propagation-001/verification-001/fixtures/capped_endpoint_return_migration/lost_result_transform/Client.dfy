include "Kernel.dfy"
include "Helper.dfy"
module Client {
  import K = Kernel
  import H = Helper
  method Target(start: int, length: int, cap: int) returns (result: int)
    requires 0 <= length
    ensures result == K.Endpoint(start,length,cap)
  {
    if start <= cap {
      var delta := H.Transfer(start,length,cap);
      result := delta;
    } else {
      result := cap;
    }
  }
}
