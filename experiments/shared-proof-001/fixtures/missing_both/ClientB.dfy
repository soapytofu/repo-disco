include "SequenceFacts.dfy"
module ClientB {
  import S = SequenceFacts
  lemma AppendPreservesLowerBound(s: seq<int>, t: seq<int>, k: nat)
    requires S.Size(t) >= k
    ensures S.Size(s + t) >= k
  {
  }
}
