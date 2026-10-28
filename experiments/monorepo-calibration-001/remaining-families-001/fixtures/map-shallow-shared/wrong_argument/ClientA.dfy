include "Kernel.dfy"
include "HelperA.dfy"
module ClientA {
  import K = Kernel`Public
  import H = HelperA
  lemma Use(m: map<int, int>, k: int, j: int, v: int, w: int)
    requires K.Valid(m) && v >= 0 && w >= 0 && k != j
    ensures K.Valid(m[k := v][j := w]) && K.FrameTwo(m, m[k := v][j := w], k, j)
  { H.Prove(m, k, v, j, w); }
}
