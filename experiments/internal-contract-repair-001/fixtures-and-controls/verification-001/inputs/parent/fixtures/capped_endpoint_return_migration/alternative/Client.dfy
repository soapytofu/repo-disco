include "Kernel.dfy"
include "Helper.dfy"
module Client {
  import K = Kernel
  import H = Helper
  method Target(start: int, length: int, cap: int) returns (result: int)
    requires 0 <= length
    ensures result == K.Endpoint(start,length,cap)
  {
    if cap < start {
      result := cap;
    } else {
      var amount := H.Transfer(start,length,cap);
      result := amount + start;
    }
  }
}
