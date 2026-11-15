include "Kernel.dfy"
include "Ops.dfy"
include "Api.dfy"
include "HelperA.dfy"
module HelperB {
  import K = Kernel`Public
  import O = Ops`Gaps
  import A = Api`Proof
  import H = HelperA
  lemma {:induction false} Prove(a: int, b: int, c: int, d: int, s: int, g: int)
    requires a <= b && c <= d && a <= s - c && s - d <= b && 0 < g && a + a + g <= s && (s - d) + (s - d) + g <= s
    ensures K.Feasible(a,b,c,d,s,g)
  {
    H.Prove(a,b,c,d,s);
    var u := if a < s - d then s - d else a;
    var v := s - u;
    if a < s - d {
      assert u == s - d;
      assert u + u + g <= s;
    } else {
      assert u == a;
      assert u + u + g <= s;
    }
    assert u + g <= v;
    O.Gap(g,u,v);
    A.Finish(a,b,c,d,s,g,u,v);
  }
}
