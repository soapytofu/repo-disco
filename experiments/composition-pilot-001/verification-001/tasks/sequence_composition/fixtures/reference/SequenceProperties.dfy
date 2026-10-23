include "SequenceFacts.dfy"
module SequenceProperties {
  import S = SequenceFacts
  export provides Nonempty, FromPositive
  opaque predicate Nonempty(s: seq<int>) { S.Size(s) > 0 }

  lemma FromPositive(s: seq<int>)
    requires S.Size(s) > 0
    ensures Nonempty(s)
  { reveal Nonempty(); }
}
