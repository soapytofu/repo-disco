include "Kernel.dfy"
include "HelperA.dfy"
module HelperB {
  import K = Kernel`Public
  import H = HelperA
  lemma {:induction false} Prove(m: map<int, int>, k: int, v: int, j: int, w: int)
    requires K.Valid(m) && v >= 0 && w >= 0 && k != j
    ensures K.Valid(m[k := v][j := w]) && K.FrameTwo(m, m[k := v][j := w], k, j)
    ensures m[k := v][j := w][k] == v && m[k := v][j := w][j] == w
  {
    H.Prove(m, k, v, j, w);
  }
}
