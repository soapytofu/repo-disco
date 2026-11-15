include "HelperB.dfy"
include "Api.dfy"
module ClientB {
  import H = HelperB
  import A = Api`Clients
  lemma Target(a: int, b: int, c: int, d: int, s: int, g: int, shift: int) returns (u: int, v: int)
    requires a <= b && c <= d && a <= s - c && s - d <= b && 0 < g && a + a + g <= s && (s - d) + (s - d) + g <= s
    ensures a+shift <= u <= b+shift && c+shift <= v <= d+shift
    ensures u + v == s+shift+shift && 0 < g && u + g <= v
  {
    H.Prove(a+shift,b+shift,c+shift,d+shift,s+shift+shift,g);
    u, v := A.Choose(a+shift,b+shift,c+shift,d+shift,s+shift+shift,g);
  }
}
