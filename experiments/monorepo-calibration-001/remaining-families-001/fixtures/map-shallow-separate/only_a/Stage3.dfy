include "Kernel.dfy"
module Stage3 {
  export Shallow provides K, Direct, Compose
  export Deep provides K, Finish, Compose
  import K = Kernel`Internal
  lemma Direct(m: map<int, int>, k: int, v: int)
    requires K.Valid(m) && v >= 0
    ensures K.Valid(m[k := v]) && K.Frame(m, m[k := v], k)
  { reveal K.Valid(); reveal K.Frame(); }
  lemma Finish(m: map<int, int>, k: int, v: int)
    requires K.Ready(m, k, v)
    ensures K.Valid(m[k := v]) && K.Frame(m, m[k := v], k)
  { reveal K.Ready(); reveal K.Values(); reveal K.Valid(); }
  lemma Compose(m: map<int, int>, k: int, v: int, j: int, w: int)
    requires k != j
    requires K.Frame(m, m[k := v], k)
    requires K.Frame(m[k := v], m[k := v][j := w], j)
    ensures K.FrameTwo(m, m[k := v][j := w], k, j)
    ensures m[k := v][j := w][k] == v && m[k := v][j := w][j] == w
  { reveal K.Frame(); reveal K.FrameTwo(); }
}
