module SequenceFacts {
  export provides Size, LengthConcat
  opaque function Size(s: seq<int>): nat { |s| }

  lemma LengthConcat(s: seq<int>, t: seq<int>)
    ensures Size(s + t) == Size(s) + Size(t)
  { reveal Size(); }
}
