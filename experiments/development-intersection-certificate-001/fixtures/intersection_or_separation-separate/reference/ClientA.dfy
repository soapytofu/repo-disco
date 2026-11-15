include "HelperA.dfy"
include "Api.dfy"
module ClientA {
  import H = HelperA
  import A = Api`Clients
  lemma Target(a: int, b: int, c: int, d: int) returns (kind: int, w: int)
    requires a <= b && c <= d
    ensures kind == -1 || kind == 0 || kind == 1
    ensures kind == 0 ==> a <= w <= b && c <= w <= d
    ensures (kind == 0) == (a <= d && c <= b)
    ensures (kind == -1) == (b < c)
    ensures (kind == 1) == (d < a)
  {
    H.Prove(a,b,c,d);
    kind, w := A.Choose(a,b,c,d);
  }
}
