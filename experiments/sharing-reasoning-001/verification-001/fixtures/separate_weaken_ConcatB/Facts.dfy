module Facts {
  export ViewA provides Size, Large, ConcatA, Finish
  export ViewB provides Size, Large, ConcatB, Finish
  opaque function Size(s: seq<int>): nat { |s| }
  opaque predicate Large(s: seq<int>, k: nat) { Size(s) > k }
  lemma ConcatA(s: seq<int>, t: seq<int>)
    ensures Size(s + t) == Size(s) + Size(t)
  { reveal Size(); }
  lemma ConcatB(s: seq<int>, t: seq<int>)
    ensures true
  { reveal Size(); }
  lemma Finish(s: seq<int>, k: nat)
    requires Size(s) > k
    ensures Large(s, k)
  { reveal Large(); }
}
