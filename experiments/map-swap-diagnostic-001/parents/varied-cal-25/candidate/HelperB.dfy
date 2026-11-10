include "Kernel.dfy"
include "Ops1.dfy"
include "Ops2.dfy"
include "Api.dfy"
module HelperB {
  import K = Kernel`Public
  import A = Api`Deep
  import O1 = Ops1`Public
  import O2 = Ops2`Public
  lemma {:induction false} Prove(s: seq<int>,i: int,j: int)
    requires 0<=i<=|s| && 0<=j<=|s|-i
    ensures K.Prefix(s,i+j)==K.Prefix(s,i)+K.Prefix(s[i..],j)
    decreases i
  {if i == 0 {
  O1.Unfold(s, j);
  O2.Expose(s, j);
  O1.Unfold(s, 0);
  O2.Expose(s, 0);
  assert K.Prefix(s, 0) == 0;
  assert K.Prefix(s, 0 + j) == K.Prefix(s, j);
  assert K.Prefix(s[0..], j) == K.Prefix(s, j);
} else {
  O1.Unfold(s, i + j);
  O2.Expose(s, i + j);
  O1.Unfold(s, i);
  O2.Expose(s, i);
  assert K.Prefix(s, i + j) == s[0] + K.Prefix(s[1..], i + j - 1);
  assert K.Prefix(s, i) == s[0] + K.Prefix(s[1..], i - 1);
  assert s[i..] == (s[1..])[i - 1..];
  Prove(s[1..], i - 1, j);
  assert K.Prefix(s[1..], i - 1 + j) == K.Prefix(s[1..], i - 1) + K.Prefix((s[1..])[i - 1..], j);
  assert K.Prefix(s, i + j) == K.Prefix(s, i) + K.Prefix(s[i..], j);
}  }
}
