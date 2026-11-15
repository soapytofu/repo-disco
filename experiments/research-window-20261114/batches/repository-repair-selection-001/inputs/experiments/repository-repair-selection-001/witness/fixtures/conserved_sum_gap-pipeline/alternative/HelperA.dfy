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
    if s - d <= a {
      O.Sum(s,a,s-a);
      O.Right(c,d,s-a);
      O.Left(a,b,a);
      A.Balance(a,b,c,d,s,a,s-a);
    } else {
      O.Sum(s,s-d,d);
      O.Right(c,d,d);
      O.Left(a,b,s-d);
      A.Balance(a,b,c,d,s,s-d,d);
    }
  }
}
