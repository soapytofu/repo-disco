include "Kernel.dfy"
module Stage1 {
  export Public provides K, Update
  import K = Kernel`Internal
  lemma Update(m: map<int, int>, k: int, v: int)
    requires K.Valid(m) && v >= 0
    ensures K.Values(m[k := v])
  { reveal K.Valid(); reveal K.Values(); }
}
