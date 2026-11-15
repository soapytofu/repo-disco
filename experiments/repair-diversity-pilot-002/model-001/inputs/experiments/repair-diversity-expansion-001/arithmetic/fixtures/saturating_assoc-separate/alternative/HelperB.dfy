include "Kernel.dfy"
include "Ops.dfy"
module HelperB {
  import K = Kernel`Public
  import O = Ops`Public
  lemma {:induction false} Prove(c: int, a: int, b: int, d: int)
    requires 0 <= c && 0 <= a && 0 <= b && 0 <= d
    ensures K.Sat(c,K.Sat(c,a,b),d) == K.Sat(c,a,K.Sat(c,b,d))
  {
    if a+b <= c {
      O.Low(c,a,b);
      if b+d <= c {
        O.Low(c,b,d);
        if a+b+d <= c {
          O.Low(c,a+b,d); O.Low(c,a,b+d);
        } else {
          O.High(c,a+b,d); O.High(c,a,b+d);
        }
      } else {
        O.High(c,b,d); O.High(c,a+b,d); O.High(c,a,c);
      }
    } else {
      O.High(c,a,b); O.High(c,c,d);
      if b+d <= c { O.Low(c,b,d); O.High(c,a,b+d); }
      else { O.High(c,b,d); O.High(c,a,c); }
    }
  }
}
