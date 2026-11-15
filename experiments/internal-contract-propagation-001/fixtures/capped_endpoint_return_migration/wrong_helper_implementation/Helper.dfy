include "Kernel.dfy"
module Helper {
  import K = Kernel
  method Transfer(start: int, length: int, cap: int) returns (r: int)
    requires 0 <= length
    requires start <= cap
    ensures 0 <= r <= length
    ensures start + r == K.Endpoint(start,length,cap)
  {
    r := length;
  }
}
