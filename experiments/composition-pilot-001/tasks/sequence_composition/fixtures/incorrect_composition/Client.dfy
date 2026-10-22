include "SequenceFacts.dfy"
include "SequenceProperties.dfy"
module Client {
  import S = SequenceFacts
  import P = SequenceProperties
  lemma AppendKeepsNonempty(s: seq<int>, t: seq<int>)
    requires S.Size(s) > 0
    ensures P.Nonempty(s + t)
  {
    S.LengthConcat(s, t);
    P.FromPositive(s);
  }
}
