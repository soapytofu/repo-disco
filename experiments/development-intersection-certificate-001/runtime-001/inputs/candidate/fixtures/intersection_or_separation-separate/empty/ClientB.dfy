include "HelperB.dfy"
include "Api.dfy"
module ClientB {
  import H = HelperB
  import A = Api`Clients
  lemma Target(a: int, b: int, c: int, d: int, shift: int) returns (kind: int, w: int)
    requires a <= b && c <= d
    ensures kind == -1 || kind == 0 || kind == 1
    ensures kind == 0 ==> c+shift <= w <= d+shift && a+shift <= w <= b+shift
    ensures (kind == 0) == (c+shift <= b+shift && a+shift <= d+shift)
    ensures (kind == -1) == (d+shift < a+shift)
    ensures (kind == 1) == (b+shift < c+shift)
  {
    H.Prove(c+shift,d+shift,a+shift,b+shift);
    kind, w := A.Choose(c+shift,d+shift,a+shift,b+shift);
  }
}
