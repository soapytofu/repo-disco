include "HelperB.dfy"
include "Api.dfy"
module ClientA {
  import H = HelperB
  import A = Api`Clients
  lemma Target(a: int, b: int, c: int, d: int, s: int, g: int) returns (u: int, v: int)
    requires a <= b && c <= d && a <= s - c && s - d <= b && 0 < g && a + a + g <= s && (s - d) + (s - d) + g <= s
    ensures a <= u <= b && c <= v <= d
    ensures u + v == s && 0 < g && u + g <= v
  {
    H.Prove(a,b,c,d,s,g);
    u, v := A.Choose(a,b,c,d,s,g);
  }
}
