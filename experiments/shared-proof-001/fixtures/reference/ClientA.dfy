include "SequenceFacts.dfy"
module ClientA {
  import S = SequenceFacts
  lemma AppendPositive(s: seq<int>, t: seq<int>)
    requires S.Size(s) > 0
    ensures S.Size(s + t) > 0
  {
    S.LengthConcat(s, t);
  }
}
