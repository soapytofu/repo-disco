include "Kernel.dfy"
module Helper {
  import K = Kernel
  method Transfer(start: int, length: int, cap: int) returns (r: int)
    requires 0 <= length
    ensures r == K.Endpoint(start,length,cap)
  {
    if start + length <= cap {
      r := start + length;
    } else {
      r := cap;
    }
  }
}
