module Facts {
  export ViewA provides Wrap, Good, Case0A, Case1A
  export ViewB provides Wrap, Good, Case0B, Case1B
  opaque function Wrap(x: int): int { x }
  opaque predicate Good(x: int) { x >= 0 }
  lemma Case0A(x: int)
    requires x >= 0
    ensures Good(Wrap(x))
  { reveal Good(), Wrap(); }
  lemma Case1A(x: int)
    requires x < 0
    ensures true
  { reveal Good(), Wrap(); }
  lemma Case0B(x: int)
    requires x >= 0
    ensures Good(Wrap(x))
  { reveal Good(), Wrap(); }
  lemma Case1B(x: int)
    requires x < 0
    ensures Good(Wrap(-x))
  { reveal Good(), Wrap(); }
}
