include "Kernel.dfy"
include "Ops.dfy"
include "Api.dfy"
module HelperA {
  import K = Kernel`Public
  import O = Ops`Bounds
  import A = Api`Bounds
  lemma {:induction false} Prove(a: int, b: int, c: int, d: int, s: int)
    requires a <= b && c <= d && a <= s - c && s - d <= b
    ensures K.Balanced(a,b,c,d,s,(if a < s - d then s - d else a),s-(if a < s - d then s - d else a))
  {
  }
}
