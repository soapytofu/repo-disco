include "Kernel.dfy"
include "HelperB.dfy"
module ClientB {
  import K = Kernel`Public
  import H = HelperB
  lemma Use(m: map<int, int>, k: int, j: int, v: int, w: int)
    requires K.Valid(m) && v >= 0 && w >= 0 && k != j
    ensures K.Valid(m[j := w][k := v]) && K.FrameTwo(m, m[j := w][k := v], j, k)
  { H.Prove(m, j, w, k, v); }
}
