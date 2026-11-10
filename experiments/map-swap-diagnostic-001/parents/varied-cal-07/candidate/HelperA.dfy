include "Kernel.dfy"
include "Ops1.dfy"
include "Ops2.dfy"
include "Api.dfy"
module HelperA {
  import K = Kernel`Public
  import A = Api`Shallow
  import O1 = Ops1`Hidden
  import O2 = Ops2`Hidden
  lemma {:induction false} Prove(s: seq<int>,i: int,j: int)
    requires 0<=i<=|s| && 0<=j<=|s|-i
    ensures K.Prefix(s,i+j)==K.Prefix(s,i)+K.Prefix(s[i..],j)
    decreases i
  {if i == 0 {
  A.Observe(s, j);
  A.Observe(s, 0);
  assert K.Prefix(s, 0) == 0;
  assert K.Prefix(s, 0 + j) == K.Prefix(s, j);
  assert K.Prefix(s, 0) + K.Prefix(s[0..], j) == 0 + K.Prefix(s, j);
} else {
  A.Observe(s, i + j);
  A.Observe(s, i);
  A.Observe(s[1..], i - 1 + j);
  A.Observe(s[1..], i - 1);
  Prove(s[1..], i - 1, j);
  assert K.Prefix(s[1..], i - 1 + j) == K.Prefix(s[1..], i - 1) + K.Prefix(s[1..][i - 1..], j);
  assert s[1..][i - 1..] == s[i..];
  assert K.Prefix(s, i + j) == s[0] + K.Prefix(s[1..], i - 1 + j);
  assert K.Prefix(s, i) == s[0] + K.Prefix(s[1..], i - 1);
  assert K.Prefix(s, i + j) == K.Prefix(s, i) + K.Prefix(s[i..], j);
}  }
}
