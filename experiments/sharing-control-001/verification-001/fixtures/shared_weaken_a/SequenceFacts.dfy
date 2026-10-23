module SequenceFacts {
  export provides Size, ConcatFactA, ConcatFactB
  opaque function Size(s: seq<int>): nat { |s| }

  lemma ConcatFactA(s: seq<int>, t: seq<int>)
    ensures true
  { reveal Size(); }

  lemma ConcatFactB(s: seq<int>, t: seq<int>)
    ensures Size(s + t) == Size(s) + Size(t)
  { reveal Size(); }
}
