include "Kernel.dfy"
module Stage2 {
  export Public provides K, Preserve
  import K = Kernel`Internal
  lemma Preserve(m: map<int, int>, k: int, v: int)
    requires K.Values(m[k := v])
    ensures K.Ready(m, k, v)
  { reveal K.Ready(); reveal K.Frame(); }
}
