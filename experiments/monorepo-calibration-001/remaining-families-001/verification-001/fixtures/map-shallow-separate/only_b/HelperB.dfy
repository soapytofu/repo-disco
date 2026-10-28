include "Kernel.dfy"
include "Stage1.dfy"
include "Stage2.dfy"
include "Stage3.dfy"
module HelperB {
  import K = Kernel`Public
  import End = Stage3`Shallow
  lemma {:induction false} Prove(m: map<int, int>, k: int, v: int, j: int, w: int)
    requires K.Valid(m) && v >= 0 && w >= 0 && k != j
    ensures K.Valid(m[k := v][j := w]) && K.FrameTwo(m, m[k := v][j := w], k, j)
    ensures m[k := v][j := w][k] == v && m[k := v][j := w][j] == w
  {
    End.Direct(m, k, v);
    End.Direct(m[k := v], j, w);
    End.Compose(m, k, v, j, w);
  }
}
