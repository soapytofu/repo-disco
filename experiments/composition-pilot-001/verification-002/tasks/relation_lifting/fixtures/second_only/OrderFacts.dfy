module OrderFacts {
  export provides Before, Transitive
  opaque predicate Before(a: int, b: int) { a <= b }

  lemma Transitive(a: int, b: int, c: int)
    requires Before(a, b) && Before(b, c)
    ensures Before(a, c)
  { reveal Before(); }
}
